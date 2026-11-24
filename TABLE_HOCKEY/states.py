"""Central state manager and menu/pause/settings/end screens."""
import json, os, pygame, config
from menu_ui import Button, Slider, Toggle, Selector, draw_text

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
        classes={"MENU":MenuState,"SETTINGS":SettingsState,"HOW_TO":HowToState,"LEADERBOARD":LeaderboardState,
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
        actions=[("START GAME",self.start),("LEADERBOARD",lambda:self.manager.change("LEADERBOARD")),
                 ("SETTINGS",lambda:self.manager.change("SETTINGS",return_to="MENU")),
                 ("HOW TO PLAY",lambda:self.manager.change("HOW_TO")),("QUIT",lambda:setattr(self.app,"running",False))]
        self.buttons=[Button((cx-155,int(h*.38)+i*55,310,46),label,cb) for i,(label,cb) in enumerate(actions)]
    def start(self): self.app.new_match(); self.manager.change("PLAYING")
    def update(self,dt):
        self.time+=dt; mouse=pygame.mouse.get_pos()
        for i,b in enumerate(self.buttons): b.update(dt,mouse,i==self.index)
    def draw(self,screen):
        w,h=screen.get_size(); screen.fill(config.COLOR_BG)
        for i in range(32):
            y=int((i/32*h+self.time*12)%h); pygame.draw.line(screen,(17,22,34),(0,y),(w,y),1)
        glow=pygame.Surface((w,h),pygame.SRCALPHA)
        pygame.draw.circle(glow,(30,90,170,24),(w//2,int(h*.25)),int(w*.34)); screen.blit(glow,(0,0))
        draw_text(screen,"TABLE HOCKEY",(w//2,int(h*.20)),int(h*.105),config.COLOR_WHITE,True)
        draw_text(screen,"ARCADE AIR HOCKEY",(w//2,int(h*.29)),25,config.COLOR_TEXT_DIM)
        for b in self.buttons: b.draw(screen)
        draw_text(screen,f"DIFFICULTY  •  {self.app.settings.get('ai_difficulty','NORMAL')}",(w//2,int(h*.83)),26,config.COLOR_GOLD)
        draw_text(screen,"W / S or ↑ / ↓   •   ENTER to select",(w//2,int(h*.91)),20,config.COLOR_TEXT_DIM)
    def handle_event(self,event):
        if event.type==pygame.KEYDOWN:
            if event.key in (pygame.K_DOWN,pygame.K_s): self.index=(self.index+1)%len(self.buttons)
            elif event.key in (pygame.K_UP,pygame.K_w): self.index=(self.index-1)%len(self.buttons)
            elif event.key in (pygame.K_RETURN,pygame.K_SPACE): self.buttons[self.index].callback()
            elif event.key==pygame.K_ESCAPE: self.app.running=False
            elif event.key in (pygame.K_LEFT,pygame.K_RIGHT):
                names=list(config.DIFFICULTY); cur=self.app.settings.get("ai_difficulty","NORMAL")
                idx=names.index(cur) if cur in names else 1
                self.app.settings.set("ai_difficulty",names[(idx+(1 if event.key==pygame.K_RIGHT else -1))%len(names)])
                self.app.settings.save()
        elif event.type==pygame.MOUSEBUTTONDOWN:
            for b in self.buttons:
                if b.handle_event(event): self.app.audio.play("click"); break

class HowToState(BaseState):
    def draw(self,screen):
        screen.fill(config.COLOR_BG); w,h=screen.get_size()
        draw_text(screen,"HOW TO PLAY",(w//2,int(h*.18)),58,config.COLOR_GOLD,True)
        lines=["Move your paddle with W A S D.","Keep the puck away from your goal and shoot into the CPU goal.",
               f"First player to {self.app.settings.win_score} goals wins.","Choose a difficulty from the main menu or Settings.",
               "Press ESC during a match to pause."]
        for i,line in enumerate(lines): draw_text(screen,line,(w//2,int(h*(.34+i*.085))),27)
        draw_text(screen,"ESC  •  BACK",(w//2,int(h*.86)),24,config.COLOR_P1)
    def handle_event(self,event):
        if event.type==pygame.KEYDOWN and event.key in (pygame.K_ESCAPE,pygame.K_RETURN,pygame.K_SPACE): self.manager.change("MENU")

class PlayingState(BaseState):
    def update(self,dt):
        self.app.match.update(dt,pygame.key.get_pressed()); self.app.match.drain_events()
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
        self.app.draw_match(screen); shade=pygame.Surface(screen.get_size(),pygame.SRCALPHA)
        shade.fill((0,0,0,185)); screen.blit(shade,(0,0))
        w,h=screen.get_size(); draw_text(screen,"PAUSED",(w//2,int(h*.27)),62,config.COLOR_GOLD,True)
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
        if self.return_to=="MENU":
            self.controls.append(Selector(rect(630,405,250,42),"DIFFICULTY",list(config.DIFFICULTY),self.app.settings.get("ai_difficulty","NORMAL"),lambda v:self._set("ai_difficulty",v)))
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
        screen.fill(config.COLOR_BG); w,h=screen.get_size()
        draw_text(screen,"SETTINGS",(w//2,65),54,config.COLOR_GOLD,True)
        draw_text(screen,"AUDIO",(330,120),25,config.COLOR_P1)
        draw_text(screen,"VIDEO & GAMEPLAY",(755,120),25,config.COLOR_P1)
        draw_text(screen,"KEY BINDINGS • CLICK AN ACTION, THEN PRESS A KEY",(360,390),18,config.COLOR_TEXT_DIM)
        for item in self.controls: item.draw(screen)
        for b in self.key_buttons+self.buttons: b.draw(screen)
        if self.awaiting_key:
            prompt = self.key_error or f"PRESS A KEY FOR {self.awaiting_key.upper()} • ESC TO CANCEL"
            draw_text(screen,prompt,(w//2,h-35),22,config.COLOR_P2_LIGHT if self.key_error else config.COLOR_GOLD)
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

class LeaderboardState(BaseState):
    """Career summary and recent match results."""
    def __init__(self, manager):
        super().__init__(manager)
        self.back = Button((35, 35, 170, 44), "BACK", lambda: self.manager.change("MENU"), config.COLOR_P2)
        try:
            with open(SCORES_PATH, "r", encoding="utf-8") as f: self.data = json.load(f)
            if not isinstance(self.data, dict): self.data = {}
        except (OSError, ValueError, TypeError): self.data = {}
    def update(self, dt): self.back.update(dt, pygame.mouse.get_pos())
    def draw(self, screen):
        screen.fill(config.COLOR_BG); w, h = screen.get_size()
        draw_text(screen, "CAREER LEADERBOARD", (w//2, 75), 48, config.COLOR_GOLD, True)
        for i, name in enumerate(("EASY", "NORMAL", "HARD", "NIGHTMARE")):
            rec = self.data.get(name, {}); wins = int(rec.get("wins", 0)); losses = int(rec.get("losses", 0))
            best = rec.get("best_time"); best_text = f"{float(best):.1f}s" if best is not None else "--"
            y = 170 + i * 58
            pygame.draw.rect(screen, config.COLOR_BG_LIGHT, (w//2-330, y-20, 660, 44), border_radius=8)
            draw_text(screen, name, (w//2-225, y), 22, config.COLOR_P1, True)
            draw_text(screen, f"W {wins}   L {losses}", (w//2, y), 22)
            draw_text(screen, f"BEST {best_text}", (w//2+225, y), 22, config.COLOR_GOLD)
        draw_text(screen, "RECENT MATCHES", (w//2, 445), 25, config.COLOR_P1, True)
        history = self.data.get("recent_matches", [])
        if not history: draw_text(screen, "No completed matches yet.", (w//2, 505), 22, config.COLOR_TEXT_DIM)
        for i, item in enumerate(history[:4]):
            label = f"{item.get('result','?')} • {item.get('difficulty','NORMAL')} • PLAYER {item.get('player_score',0)} - CPU {item.get('cpu_score',0)} • {float(item.get('duration',0)):.1f}s"
            draw_text(screen, label, (w//2, 485+i*38), 19, config.COLOR_P1_LIGHT if item.get("result")=="WIN" else config.COLOR_P2_LIGHT)
        self.back.draw(screen)
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE): self.manager.change("MENU")
        self.back.handle_event(event)

class EndState(BaseState):
    def __init__(self,manager):
        super().__init__(manager); self.victory=manager.current_name=="VICTORY"; self.match=self.app.match
        self.record=self._record(); w,h=self.app.screen.get_size(); cx=w//2
        self.buttons=[Button((cx-155,int(h*.69),310,46),"PLAY AGAIN",self.again),
                      Button((cx-155,int(h*.77),310,46),"MAIN MENU",self.menu),
                      Button((cx-155,int(h*.85),310,46),"QUIT",lambda:setattr(self.app,"running",False))]
        self.index=0
    def _record(self):
        """Persist career totals and a short match history."""
        import datetime
        os.makedirs(SAVE_DIR, exist_ok=True)
        try:
            with open(SCORES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError, TypeError):
            data = {}
        if not isinstance(data, dict): data = {}
        difficulty = self.app.settings.get("ai_difficulty", "NORMAL")
        record = data.get(difficulty, {})
        if not isinstance(record, dict): record = {}
        wins, losses = int(record.get("wins", 0) or 0), int(record.get("losses", 0) or 0)
        matches = int(record.get("matches", wins + losses) or 0)
        streak = int(record.get("current_streak", 0) or 0)
        if self.victory: wins += 1; streak = max(0, streak) + 1
        else: losses += 1; streak = min(0, streak) - 1
        matches += 1
        try: best = float(record.get("best_time"))
        except (TypeError, ValueError): best = None
        new_best = bool(self.victory and (best is None or self.match.match_time < best))
        if new_best: best = round(self.match.match_time, 2)
        record.update({"wins":wins,"losses":losses,"matches":matches,"current_streak":streak,"best_time":best})
        data[difficulty] = record
        history = data.get("recent_matches", [])
        if not isinstance(history, list): history = []
        history.insert(0, {"date":datetime.datetime.now().isoformat(timespec="seconds"),
            "difficulty":difficulty,"result":"WIN" if self.victory else "LOSS",
            "player_score":self.match.players[0].score,"cpu_score":self.match.players[1].score,
            "duration":round(self.match.match_time,2)})
        data["recent_matches"] = history[:20]
        try:
            with open(SCORES_PATH, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
        except (OSError, TypeError, ValueError) as exc:
            print("[career] could not save match record:", exc)
        return new_best
    def again(self): self.app.new_match(); self.manager.change("PLAYING")
    def menu(self): self.app.new_match(); self.manager.change("MENU")
    def update(self,dt):
        self.match.effects.update(dt); mouse=pygame.mouse.get_pos()
        for i,b in enumerate(self.buttons): b.update(dt,mouse,i==self.index)
    def draw(self,screen):
        self.app.draw_match(screen); shade=pygame.Surface(screen.get_size(),pygame.SRCALPHA)
        shade.fill((0,0,0,205)); screen.blit(shade,(0,0)); w,h=screen.get_size()
        draw_text(screen,"VICTORY!" if self.victory else "GAME OVER",(w//2,int(h*.16)),64,config.COLOR_GOLD if self.victory else config.COLOR_P2_LIGHT,True)
        draw_text(screen,f"PLAYER {self.match.players[0].score}  —  CPU {self.match.players[1].score}",(w//2,int(h*.29)),32)
        draw_text(screen,f"TIME PLAYED  {self.app._format_time(self.match.match_time)}",(w//2,int(h*.37)),25)
        draw_text(screen,f"DIFFICULTY  {self.app.settings.get('ai_difficulty','NORMAL')}",(w//2,int(h*.43)),25,config.COLOR_GOLD)
        draw_text(screen,f"GOALS SCORED  {self.match.players[0].score}",(w//2,int(h*.49)),24)
        status = "NEW BEST TIME!" if self.victory and self.record else ("CAREER WIN SAVED" if self.victory else "HIGH SCORE RETAINED")
        draw_text(screen,status,(w//2,int(h*.55)),21,config.COLOR_TEXT_DIM)
        for b in self.buttons: b.draw(screen)
    def handle_event(self,event):
        if event.type==pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN,pygame.K_SPACE): self.buttons[self.index].callback(); return
            if event.key in (pygame.K_DOWN,pygame.K_s): self.index=(self.index+1)%len(self.buttons)
            elif event.key in (pygame.K_UP,pygame.K_w): self.index=(self.index-1)%len(self.buttons)
            elif event.key==pygame.K_ESCAPE: self.menu(); return
        for b in self.buttons:
            if b.handle_event(event): self.app.audio.play("click"); break
