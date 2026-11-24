"""Central state manager and menu/pause/settings/end screens."""
import json, os, pygame, config
from menu_ui import Button, Slider, Toggle, Selector, draw_text, draw_arcade_background, draw_arcade_panel
from skins import get_skin_name

SAVE_DIR=os.path.join(os.path.dirname(os.path.abspath(__file__)),"save")
SCORES_PATH=os.path.join(SAVE_DIR,"high_scores.json")

class BaseState:
    def __init__(self,manager): self.manager=manager; self.app=manager.app
    def update(self,dt): pass
    def draw(self,screen): pass
    def handle_event(self,event): pass

class StateManager:
    """Only the active screen receives update, draw and input."""
    def __init__(self,app):
        self.app=app; self.current_name="MENU"; self.active=MenuState(self)
        self.fade_time=.42; self.fade_elapsed=self.fade_time
    def change(self,name,**kwargs):
        classes={"MENU":MenuState,"LEVEL_SELECT":LevelSelectState,"SETTINGS":SettingsState,"HOW_TO":HowToState,
                 "PLAYING":PlayingState,"PAUSED":PauseState,"GAME_OVER":EndState,"VICTORY":EndState}
        self.current_name=name
        self.active=classes[name](self,**kwargs) if kwargs else classes[name](self)
        self.fade_elapsed=0.0
    def update(self,dt):
        self.active.update(dt); self.fade_elapsed=min(self.fade_time,self.fade_elapsed+dt)
    def draw(self,screen):
        self.active.draw(screen)
        if self.fade_elapsed<self.fade_time:
            layer=pygame.Surface(screen.get_size(),pygame.SRCALPHA)
            layer.fill((0,0,0,int(255*(1-self.fade_elapsed/self.fade_time))))
            screen.blit(layer,(0,0))
    def handle_event(self,event): self.active.handle_event(event)

class MenuState(BaseState):
    def __init__(self,manager):
        super().__init__(manager); self.time=0.; self.index=0; self._layout()
    def _layout(self):
        w,h=self.app.screen.get_size(); cx=w//2
        actions=[("START GAME",self.start),("SETTINGS",lambda:self.manager.change("SETTINGS",return_to="MENU")),
                 ("HOW TO PLAY",lambda:self.manager.change("HOW_TO")),("QUIT",lambda:setattr(self.app,"running",False))]
        self.buttons=[Button((cx-155,int(h*.38)+i*55,310,46),label,cb) for i,(label,cb) in enumerate(actions)]
    def start(self): self.manager.change("LEVEL_SELECT")
    def update(self,dt):
        self.time+=dt; mouse=pygame.mouse.get_pos()
        for i,b in enumerate(self.buttons): b.update(dt,mouse,i==self.index)
    def draw(self,screen):
        w,h=screen.get_size()
        draw_arcade_background(screen,self.time,"TABLE HOCKEY",
            f"ARCADE AIR HOCKEY  •  CPU SKILL RISES WITH EVERY LEVEL  •  {self.app.current_level:02d}/30")
        panel=(w//2-int(w*.19),int(h*.32),int(w*.38),int(h*.43))
        draw_arcade_panel(screen,panel,config.COLOR_P1,230)
        for b in self.buttons: b.draw(screen)
        draw_text(screen,"W / S OR ARROWS  •  ENTER TO SELECT  •  MOUSE TO NAVIGATE",
                  (w//2,int(h*.92)),max(14,int(h*.025)),config.COLOR_TEXT_DIM)
    def handle_event(self,event):
        if event.type==pygame.KEYDOWN:
            if event.key in (pygame.K_DOWN,pygame.K_s): self.index=(self.index+1)%len(self.buttons)
            elif event.key in (pygame.K_UP,pygame.K_w): self.index=(self.index-1)%len(self.buttons)
            elif event.key in (pygame.K_RETURN,pygame.K_SPACE): self.buttons[self.index].callback()
            elif event.key==pygame.K_ESCAPE: self.app.running=False
        elif event.type==pygame.MOUSEBUTTONDOWN:
            for b in self.buttons:
                if b.handle_event(event): self.app.audio.play("click"); break

class LevelSelectState(BaseState):
    """Campaign map: only levels reached through victories are selectable."""
    def __init__(self,manager):
        super().__init__(manager)
        self.index=0
        self.unlocked=self._load_unlocked()
        self._build()

    def _load_unlocked(self):
        # Read the saved campaign frontier, not the last replayed level.
        try:
            with open(SCORES_PATH,"r",encoding="utf-8") as f:
                data=json.load(f)
            value=data.get("current_level",self.app.current_level) if isinstance(data,dict) else self.app.current_level
            return max(1,min(30,int(value)))
        except (OSError,ValueError,TypeError,AttributeError):
            return max(1,min(30,int(self.app.current_level)))

    def _build(self):
        w,h=self.app.screen.get_size()
        sx,sy=w/1280,h/720
        cols=5
        gap=int(14*sx)
        bw=int(150*sx)
        bh=int(58*sy)
        total=cols*bw+(cols-1)*gap
        left=(w-total)//2
        top=int(h*.29)
        self.level_buttons=[]
        for level in range(1,31):
            row,col=divmod(level-1,cols)
            rect=(left+col*(bw+gap),top+row*(bh+int(13*sy)),bw,bh)
            unlocked=level<=self.unlocked
            label=f"LEVEL {level:02d}" if unlocked else f"LOCKED  {level:02d}"
            button=Button(rect,label,lambda n=level:self.select_level(n),
                          config.COLOR_GOLD if level==self.app.current_level else config.COLOR_P1)
            button.enabled=unlocked
            self.level_buttons.append(button)
        self.back_button=Button((w//2-int(125*sx),int(h*.86),int(250*sx),int(46*sy)),
                                "BACK TO MENU",lambda:self.manager.change("MENU"),config.COLOR_P2)

    def select_level(self,level):
        if level<1 or level>self.unlocked: return
        self.app.current_level=level
        self.app.new_match()
        self.manager.change("PLAYING")

    def update(self,dt):
        mouse=pygame.mouse.get_pos()
        for i,b in enumerate(self.level_buttons): b.update(dt,mouse,i==self.index)
        self.back_button.update(dt,mouse)

    def draw(self,screen):
        w,h=screen.get_size()
        draw_arcade_background(screen,self.app.game_time,"CAMPAIGN SELECT",
            f"SECTOR ACCESS  •  {self.unlocked:02d} / 30 LEVELS UNLOCKED")
        grid_rect=(int(w*.12),int(h*.265),int(w*.76),int(h*.49))
        draw_arcade_panel(screen,grid_rect,config.COLOR_P1,205)
        for i,b in enumerate(self.level_buttons):
            if i+1==self.app.current_level and b.enabled:
                pygame.draw.rect(screen,(255,200,90),b.rect.inflate(8,7),2,border_radius=10)
            b.draw(screen)
        self.back_button.draw(screen)
        draw_text(screen,"CLEAR A LEVEL TO UNLOCK THE NEXT • CPU GETS SMARTER EVERY LEVEL",
                  (w//2,int(h*.245)),max(13,int(h*.020)),config.COLOR_GOLD)

    def handle_event(self,event):
        if event.type==pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE,pygame.K_BACKSPACE):
                self.manager.change("MENU"); return
            if event.key in (pygame.K_LEFT,pygame.K_a): self.index=(self.index-1)%30
            elif event.key in (pygame.K_RIGHT,pygame.K_d): self.index=(self.index+1)%30
            elif event.key in (pygame.K_UP,pygame.K_w): self.index=(self.index-5)%30
            elif event.key in (pygame.K_DOWN,pygame.K_s): self.index=(self.index+5)%30
            elif event.key in (pygame.K_RETURN,pygame.K_SPACE):
                self.level_buttons[self.index].callback() if self.level_buttons[self.index].enabled else None
        if event.type==pygame.MOUSEBUTTONDOWN:
            if self.back_button.handle_event(event):
                self.app.audio.play("click"); return
            for b in self.level_buttons:
                if b.handle_event(event):
                    self.app.audio.play("click"); return


class HowToState(BaseState):
    def draw(self,screen):
        w,h=screen.get_size()
        draw_arcade_background(screen,self.app.game_time,"HOW TO PLAY","QUICK START • MASTER THE TABLE")
        panel=(int(w*.16),int(h*.29),int(w*.68),int(h*.48))
        draw_arcade_panel(screen,panel,config.COLOR_P1,225)
        lines=["01   MOVE YOUR PADDLE  •  MOVE THE MOUSE",
               "02   DEFEND YOUR GOAL AND ATTACK THE CPU",
               f"03   FIRST TO {self.app.settings.win_score} GOALS WINS THE MATCH",
               "04   CPU GETS SMARTER WITH EVERY CAMPAIGN LEVEL",
               "05   PRESS ESC OR P TO PAUSE THE MATCH"]
        for i,line in enumerate(lines):
            draw_text(screen,line,(w//2,int(h*(.37+i*.078))),max(18,int(h*.032)),
                      config.COLOR_GOLD if i==3 else config.COLOR_TEXT,i==3)
        draw_text(screen,"ESC  •  BACK",(w//2,int(h*.86)),22,config.COLOR_P1)
    def handle_event(self,event):
        if event.type==pygame.KEYDOWN and event.key in (pygame.K_ESCAPE,pygame.K_RETURN,pygame.K_SPACE): self.manager.change("MENU")

class PlayingState(BaseState):
    def update(self,dt):
        self.app.match.update(
            dt, pygame.key.get_pressed(), mouse_position=pygame.mouse.get_pos()
        )
        self.app.match.drain_events()
        if self.app.match.state=="GAMEOVER":
            self.manager.change("VICTORY" if self.app.match.winner==1 else "GAME_OVER")
    def draw(self,screen): self.app.draw_match(screen)
    def handle_event(self,event):
        if event.type==pygame.KEYDOWN and event.key in (pygame.K_ESCAPE,pygame.K_p) and self.app.match.is_active:
            self.app.match.pause(); self.manager.change("PAUSED")

class PauseState(BaseState):
    def __init__(self,manager):
        super().__init__(manager); w,h=self.app.screen.get_size(); cx=w//2; self.index=0
        actions=[("RESUME",lambda:self.resume()),("SETTINGS",lambda:self.manager.change("SETTINGS",return_to="PAUSED")),
                 ("RESTART",self.restart),("MAIN MENU",self.menu)]
        self.buttons=[Button((cx-145,int(h*.39)+i*58,290,46),t,cb) for i,(t,cb) in enumerate(actions)]
    def resume(self): self.app.match.resume(); self.manager.change("PLAYING")
    def restart(self): self.app.new_match(); self.manager.change("PLAYING")
    def menu(self): self.app.new_match(); self.manager.change("MENU")
    def update(self,dt):
        mouse=pygame.mouse.get_pos()
        for i,b in enumerate(self.buttons): b.update(dt,mouse,i==self.index)
    def draw(self,screen):
        self.app.draw_match(screen); w,h=screen.get_size()
        shade=pygame.Surface((w,h),pygame.SRCALPHA); shade.fill((2,5,13,205)); screen.blit(shade,(0,0))
        panel=(w//2-205,int(h*.20),410,int(h*.62))
        draw_arcade_panel(screen,panel,config.COLOR_GOLD,235)
        draw_text(screen,"MATCH PAUSED",(w//2,int(h*.29)),58,config.COLOR_GOLD,True)
        draw_text(screen,f"LEVEL {self.app.match.level:02d}  •  SCORE {self.app.match.players[0].score} - {self.app.match.players[1].score}",
                  (w//2,int(h*.37)),22,config.COLOR_TEXT_DIM)
        for b in self.buttons: b.draw(screen)
    def handle_event(self,event):
        if event.type==pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE,pygame.K_p): self.resume(); return
            if event.key in (pygame.K_DOWN,pygame.K_s): self.index=(self.index+1)%len(self.buttons)
            elif event.key in (pygame.K_UP,pygame.K_w): self.index=(self.index-1)%len(self.buttons)
            elif event.key in (pygame.K_RETURN,pygame.K_SPACE): self.buttons[self.index].callback(); return
        for b in self.buttons:
            if b.handle_event(event): self.app.audio.play("click"); break

class SettingsState(BaseState):
    def __init__(self,manager,return_to="MENU"):
        super().__init__(manager); self.return_to=return_to; self.snapshot=dict(self.app.settings.data)
        self.awaiting_key=None; self.key_error=None; self.controls=[]; self.buttons=[]; self.key_buttons=[]; self._build()
    def _set(self,key,value): self.app.settings.set(key,value); self.app._apply_audio()
    def _build(self):
        w,h=self.app.screen.get_size(); sx,sy=w/1280,h/720
        def rect(x,y,rw,rh): return (int(x*sx),int(y*sy),int(rw*sx),int(rh*sy))
        self.controls=[
            Slider(rect(180,175,300,10),"MASTER",self.app.settings.get("master_volume",.8),lambda v:self._set("master_volume",v)),
            Slider(rect(180,255,300,10),"MUSIC",self.app.settings.get("music_volume",.35),lambda v:self._set("music_volume",v)),
            Slider(rect(180,335,300,10),"SFX",self.app.settings.get("sfx_volume",.8),lambda v:self._set("sfx_volume",v)),
            Toggle(rect(740,165,56,28),"FULLSCREEN",self.app.settings.fullscreen,lambda v:self._set("fullscreen",v)),
            Toggle(rect(740,220,56,28),"FPS COUNTER",self.app.settings.get("show_fps",True),lambda v:self._set("show_fps",v)),
            Toggle(rect(740,275,56,28),"SCREEN SHAKE",self.app.settings.get("screen_shake",True),lambda v:self._set("screen_shake",v)),
            Toggle(rect(740,330,56,28),"MUSIC ENABLED",self.app.settings.get("music_enabled",True),lambda v:self._set("music_enabled",v)),
        ]
        self.controls += [
            Selector(rect(630,465,250,42),"RESOLUTION",[f"{x}x{y}" for x,y in config.RESOLUTIONS],f"{self.app.settings.resolution[0]}x{self.app.settings.resolution[1]}",self._resolution),
            Selector(rect(630,525,250,42),"FPS CAP",["30","60","120","UNLIMITED"],str(self.app.settings.get("fps_cap",60)) if self.app.settings.get("fps_cap",60) else "UNLIMITED",self._fps),
            Selector(rect(630,575,250,36),"GRAPHICS",["LOW","MEDIUM","HIGH"],self.app.settings.get("graphics_quality","HIGH"),lambda v:self._set("graphics_quality",v)),
            Selector(rect(630,615,250,32),"TABLE THEME",["NEON","CYBER","SUNSET"],self.app.settings.get("table_theme","NEON"),lambda v:self._set("table_theme",v))]
        binds=self.app.settings.get("keybindings",{})
        defaults={"up":"w","left":"a","down":"s","right":"d"}
        for i,action in enumerate(("up","left","down","right")):
            key=binds.get(action,defaults[action])
            self.key_buttons.append(Button(rect(175,425+i*45,190,36),f"{action.upper()}: {str(key).upper()}",lambda a=action:self._capture(a),config.COLOR_GOLD))
        self.buttons=[Button(rect(405,660,180,42),"APPLY",self.apply),Button(rect(610,660,180,42),"BACK / CANCEL",self.cancel,config.COLOR_P2),Button(rect(815,660,205,42),"RESET DEFAULTS",self.reset,config.COLOR_GOLD)]
    def _resolution(self,value):
        x,y=value.split("x"); self._set("resolution",(int(x),int(y)))
    def _fps(self,value): self._set("fps_cap",0 if value=="UNLIMITED" else int(value))
    def _capture(self,action): self.awaiting_key=action; self.key_error=None
    def reset(self):
        from config import DEFAULT_SETTINGS
        import copy
        self.app.settings.data=copy.deepcopy(DEFAULT_SETTINGS); self._build(); self.app._apply_audio()
    def apply(self):
        self.app.apply_runtime_settings(rebuild_video=True); self.app.settings.save(); self.manager.change(self.return_to)
    def cancel(self):
        self.app.settings.data=self.snapshot; self.app.apply_runtime_settings(rebuild_video=True); self.manager.change(self.return_to)
    def update(self,dt):
        mouse=pygame.mouse.get_pos()
        for b in self.key_buttons+self.buttons: b.update(dt,mouse)
    def draw(self,screen):
        w,h=screen.get_size()
        draw_arcade_background(screen,self.app.game_time,"SYSTEM SETTINGS","TUNE YOUR ARCADE EXPERIENCE")
        draw_arcade_panel(screen,(int(w*.07),int(h*.20),int(w*.40),int(h*.64)),config.COLOR_P1,220)
        draw_arcade_panel(screen,(int(w*.53),int(h*.20),int(w*.40),int(h*.64)),config.COLOR_P2,220)
        draw_text(screen,"AUDIO & CONTROLS",(int(w*.27),int(h*.25)),24,config.COLOR_P1,True)
        draw_text(screen,"VIDEO & GAMEPLAY",(int(w*.73),int(h*.25)),24,config.COLOR_P2,True)
        draw_text(screen,"KEY BINDINGS • SELECT AN ACTION, THEN PRESS A KEY",
                  (int(w*.28),int(h*.55)),17,config.COLOR_TEXT_DIM)
        for item in self.controls: item.draw(screen)
        for b in self.key_buttons+self.buttons: b.draw(screen)
        if self.awaiting_key:
            prompt=self.key_error or f"PRESS A KEY FOR {self.awaiting_key.upper()} • ESC TO CANCEL"
            draw_text(screen,prompt,(w//2,int(h*.95)),20,
                      config.COLOR_P2_LIGHT if self.key_error else config.COLOR_GOLD)
    def handle_event(self,event):
        if self.awaiting_key and event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE: self.awaiting_key=None; self.key_error=None; return
            keyname=pygame.key.name(event.key); binds=dict(self.app.settings.get("keybindings",{}))
            if keyname in binds.values() and binds.get(self.awaiting_key) != keyname:
                self.key_error="THAT KEY IS ALREADY ASSIGNED"
                self.app.audio.play("wall")
                return
            binds[self.awaiting_key]=keyname; self.app.settings.set("keybindings",binds)
            for b in self.key_buttons:
                action=b.label.split(":")[0].lower()
                if action==self.awaiting_key: b.label=f"{action.upper()}: {keyname.upper()}"
            self.awaiting_key=None; self.key_error=None; return
        for item in self.controls:
            if item.handle_event(event): return
        for b in self.key_buttons+self.buttons:
            if b.handle_event(event): self.app.audio.play("click"); return
        if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE: self.cancel()

class EndState(BaseState):
    def __init__(self,manager):
        super().__init__(manager); self.victory=manager.current_name=="VICTORY"; self.match=self.app.match
        self.record=self._record(); self.reward_skin_id=self.match.level if self.victory else 0
        self.reward_skin_new=bool(self.victory and self.reward_skin_id in self.record.get("new_skins", []))
        w,h=self.app.screen.get_size(); cx=w//2
        self.buttons=[Button((cx-155,int(h*.69),310,46),"PLAY AGAIN",self.again),
                      Button((cx-155,int(h*.77),310,46),"MAIN MENU",self.menu),
                      Button((cx-155,int(h*.85),310,46),"QUIT",lambda:setattr(self.app,"running",False))]
        self.index=0
    def _record(self):
        """Persist campaign progress; winning advances one level, losing retries."""
        os.makedirs(SAVE_DIR, exist_ok=True)
        try:
            with open(SCORES_PATH, "r", encoding="utf-8") as f: data = json.load(f)
            if not isinstance(data, dict): data = {}
        except (OSError, ValueError, TypeError): data = {}
        level = max(1, min(30, int(getattr(self.match, "level", 1))))
        levels = data.get("levels", {})
        if not isinstance(levels, dict): levels = {}
        record = levels.get(str(level), {})
        if not isinstance(record, dict): record = {}
        record["completed"] = bool(record.get("completed", False) or self.victory)
        record["attempts"] = int(record.get("attempts", 0) or 0) + 1
        record["wins"] = int(record.get("wins", 0) or 0) + (1 if self.victory else 0)
        record["losses"] = int(record.get("losses", 0) or 0) + (0 if self.victory else 1)
        levels[str(level)] = record
        data["levels"] = levels
        current = max(1, min(30, int(data.get("current_level", 1) or 1)))
        if self.victory and level >= current: current = min(30, level + 1)
        data["current_level"] = current
        unlocked_skins = data.get("unlocked_skins", [])
        if not isinstance(unlocked_skins, list): unlocked_skins = []
        unlocked_skins = sorted({max(1, min(30, int(x))) for x in unlocked_skins if str(x).isdigit()})
        new_skins = []
        if self.victory:
            if level not in unlocked_skins:
                unlocked_skins.append(level)
                unlocked_skins.sort()
                new_skins.append(level)
            data["equipped_skin"] = level
            self.app.player_skin_id = level
            self.match.paddles[0].skin_id = level
        data["unlocked_skins"] = unlocked_skins
        self.app.unlocked_skins = unlocked_skins
        self.app.current_level = current
        try:
            with open(SCORES_PATH, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
        except (OSError, TypeError, ValueError) as exc:
            print("[campaign] could not save progress:", exc)
        return {"new_skins": new_skins, "unlocked_skins": unlocked_skins}
    def again(self): self.app.new_match(); self.manager.change("PLAYING")
    def menu(self): self.app.new_match(); self.manager.change("MENU")
    def update(self,dt):
        self.match.effects.update(dt); mouse=pygame.mouse.get_pos()
        for i,b in enumerate(self.buttons): b.update(dt,mouse,i==self.index)
    def draw(self,screen):
        self.app.draw_match(screen); w,h=screen.get_size()
        shade=pygame.Surface((w,h),pygame.SRCALPHA); shade.fill((2,5,13,218)); screen.blit(shade,(0,0))
        panel=(w//2-int(w*.25),int(h*.09),int(w*.50),int(h*.84))
        draw_arcade_panel(screen,panel,config.COLOR_GOLD if self.victory else config.COLOR_P2,240)
        heading="ROUND CLEARED!" if self.victory else "MATCH OVER"
        draw_text(screen,heading,(w//2,int(h*.17)),max(38,int(h*.075)),
                  config.COLOR_GOLD if self.victory else config.COLOR_P2_LIGHT,True)
        draw_text(screen,f"PLAYER {self.match.players[0].score}  —  CPU {self.match.players[1].score}",
                  (w//2,int(h*.29)),32)
        draw_text(screen,f"TIME  {self.app._format_time(self.match.match_time)}",
                  (w//2,int(h*.37)),23,config.COLOR_TEXT_DIM)
        draw_text(screen,f"CAMPAIGN LEVEL  {self.match.level:02d} / 30",
                  (w//2,int(h*.44)),26,config.COLOR_GOLD,True)
        status="LEVEL 30 MASTERED!" if self.victory and self.match.level>=30 else (f"LEVEL {self.match.level+1} UNLOCKED!" if self.victory else f"RETRY LEVEL {self.match.level}")
        draw_text(screen,status,(w//2,int(h*.53)),23,config.COLOR_TEXT)
        if self.victory:
            reward = get_skin_name(self.match.level)
            reward_text = ("NEW PLAYER SKIN UNLOCKED!" if self.reward_skin_new else "PLAYER SKIN EARNED")
            draw_text(screen,reward_text,(w//2,int(h*.59)),21,config.COLOR_GOLD,True)
            draw_text(screen,f"{reward}  •  NOW EQUIPPED",(w//2,int(h*.635)),20,config.COLOR_TEXT)
        for b in self.buttons: b.draw(screen)
    def handle_event(self,event):
        if event.type==pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN,pygame.K_SPACE): self.buttons[self.index].callback(); return
            if event.key in (pygame.K_DOWN,pygame.K_s): self.index=(self.index+1)%len(self.buttons)
            elif event.key in (pygame.K_UP,pygame.K_w): self.index=(self.index-1)%len(self.buttons)
            elif event.key==pygame.K_ESCAPE: self.menu(); return
        for b in self.buttons:
            if b.handle_event(event): self.app.audio.play("click"); break
