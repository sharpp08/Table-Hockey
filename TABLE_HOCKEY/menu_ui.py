"""Small, reusable menu widgets for Table Hockey."""
import pygame
import config

def draw_text(surface, text, center, size=30, color=config.COLOR_TEXT, bold=False):
    font = pygame.font.Font(None, max(14, int(size)))
    font.set_bold(bool(bold))
    image = font.render(str(text), True, color)
    surface.blit(image, image.get_rect(center=center))
    return image.get_rect(center=center)

def draw_arcade_background(surface, time=0.0, title=None, subtitle=None):
    """Shared dark neon arena treatment for every non-gameplay screen."""
    w,h=surface.get_size()
    surface.fill((6,9,17))
    # Deep vertical color atmosphere.
    for i in range(28):
        y=int(i*h/28)
        f=0.72+0.28*(i/27)
        color=(int(8*f),int(13*f),int(25*f))
        pygame.draw.line(surface,color,(0,y),(w,y))
    # Perspective floor grid.
    horizon=int(h*.57)
    grid=pygame.Surface((w,h),pygame.SRCALPHA)
    for i in range(17):
        y=horizon+int((i/16)**1.7*(h-horizon))
        pygame.draw.line(grid,(37,92,139,25),(0,y),(w,y),1)
    for i in range(-12,13):
        x=w//2+i*int(w*.055)
        pygame.draw.line(grid,(37,92,139,22),(w//2,horizon),(x,h),1)
    surface.blit(grid,(0,0))
    # Moving energy streaks.
    for i in range(12):
        x=int((i/12*w + time*34)%(w+80))-40
        y=int(h*.12+(i*71)%max(1,int(h*.42)))
        pygame.draw.line(surface,(15,42,65),(x,y),(x+38,y),2)
    # Framing rails and corner ticks.
    margin=max(14,int(min(w,h)*.025))
    frame=pygame.Rect(margin,margin,w-2*margin,h-2*margin)
    pygame.draw.rect(surface,(23,48,70),frame,1,border_radius=12)
    tick=max(18,int(w*.025))
    for x,sgn in ((frame.left,1),(frame.right,-1)):
        for y,ys in ((frame.top,1),(frame.bottom,-1)):
            pygame.draw.line(surface,(55,151,210),(x,y),(x+sgn*tick,y),3)
            pygame.draw.line(surface,(55,151,210),(x,y),(x,y+ys*tick),3)
    if title:
        draw_text(surface,title,(w//2,int(h*.105)),max(34,int(h*.075)),config.COLOR_WHITE,True)
        pygame.draw.line(surface,config.COLOR_P1,(int(w*.36),int(h*.17)),(int(w*.64),int(h*.17)),2)
    if subtitle:
        draw_text(surface,subtitle,(w//2,int(h*.205)),max(16,int(h*.027)),config.COLOR_TEXT_DIM)

def draw_arcade_panel(surface, rect, accent=config.COLOR_P1, alpha=225):
    panel=pygame.Surface((rect[2],rect[3]),pygame.SRCALPHA)
    pygame.draw.rect(panel,(10,16,28,alpha),panel.get_rect(),border_radius=14)
    pygame.draw.rect(panel,(*accent,170),panel.get_rect(),2,border_radius=14)
    pygame.draw.line(panel,(*accent,110),(18,3),(rect[2]-18,3),2)
    surface.blit(panel,rect[:2])

class Button:
    def __init__(self, rect, label, callback=None, accent=config.COLOR_P1):
        self.rect=pygame.Rect(rect); self.label=label; self.callback=callback
        self.accent=accent; self.hover=0.0; self.enabled=True
    def update(self, dt, mouse, focused=False):
        target=1.0 if self.enabled and (self.rect.collidepoint(mouse) or focused) else 0.0
        self.hover += (target-self.hover)*min(1.0,dt*13.0)
    def draw(self, surface):
        r=self.rect.copy()
        if self.hover: r.inflate_ip(int(7*self.hover),int(4*self.hover))
        bg=(18,25,40) if self.enabled else (13,17,27)
        pygame.draw.rect(surface,(5,8,15),r.move(0,4),border_radius=8)
        pygame.draw.rect(surface,bg,r,border_radius=8)
        edge=self.accent if self.hover>.12 and self.enabled else (47,61,83)
        pygame.draw.rect(surface,edge,r,2,border_radius=8)
        bar=pygame.Rect(r.left+2,r.top+7,4,r.height-14)
        pygame.draw.rect(surface,self.accent if self.enabled else (55,62,76),bar,border_radius=2)
        if self.hover>.08 and self.enabled:
            glow=pygame.Surface((r.w,r.h),pygame.SRCALPHA)
            pygame.draw.rect(glow,(*self.accent,int(22+35*self.hover)),glow.get_rect(),border_radius=8)
            surface.blit(glow,r.topleft)
            pygame.draw.line(surface,self.accent,(r.left+14,r.top+2),(r.right-14,r.top+2),2)
        draw_text(surface,self.label,r.center,max(20,int(r.h*.43)),
                  config.COLOR_WHITE if self.enabled else (94,103,120),True)
    def handle_event(self,event):
        if self.enabled and event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and self.rect.collidepoint(event.pos):
            if self.callback: self.callback()
            return True
        return False

class Slider:
    def __init__(self,rect,label,value,callback):
        self.rect=pygame.Rect(rect); self.label=label; self.value=max(0.0,min(1.0,float(value)))
        self.callback=callback; self.dragging=False
    def _set(self,x):
        self.value=max(0.0,min(1.0,(x-self.rect.x)/max(1,self.rect.w))); self.callback(self.value)
    def handle_event(self,event):
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and self.rect.inflate(0,28).collidepoint(event.pos):
            self.dragging=True; self._set(event.pos[0]); return True
        if event.type==pygame.MOUSEMOTION and self.dragging: self._set(event.pos[0]); return True
        if event.type==pygame.MOUSEBUTTONUP and event.button==1 and self.dragging:
            self.dragging=False; return True
        return False
    def draw(self,surface):
        draw_text(surface,f"{self.label}: {round(self.value*100)}%",(self.rect.centerx,self.rect.y-15),23)
        pygame.draw.rect(surface,config.COLOR_TABLE_EDGE,self.rect,border_radius=6)
        fill=self.rect.copy(); fill.w=int(fill.w*self.value)
        pygame.draw.rect(surface,config.COLOR_P1,fill,border_radius=6)
        pygame.draw.circle(surface,config.COLOR_WHITE,(self.rect.x+int(self.rect.w*self.value),self.rect.centery),9)

class Toggle:
    def __init__(self,rect,label,value,callback):
        self.rect=pygame.Rect(rect); self.label=label; self.value=bool(value); self.callback=callback
    def handle_event(self,event):
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and self.rect.collidepoint(event.pos):
            self.value=not self.value; self.callback(self.value); return True
        return False
    def draw(self,surface):
        draw_text(surface,self.label,(self.rect.left-95,self.rect.centery),23)
        pygame.draw.rect(surface,config.COLOR_P1 if self.value else config.COLOR_TABLE_EDGE,self.rect,border_radius=12)
        pygame.draw.circle(surface,config.COLOR_WHITE,(self.rect.right-12 if self.value else self.rect.left+12,self.rect.centery),9)

class Selector:
    def __init__(self,rect,label,options,value,callback):
        self.rect=pygame.Rect(rect); self.label=label; self.options=list(options)
        self.value=value if value in self.options else self.options[0]; self.callback=callback
    def handle_event(self,event):
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and self.rect.collidepoint(event.pos):
            self.value=self.options[(self.options.index(self.value)+1)%len(self.options)]
            self.callback(self.value); return True
        return False
    def draw(self,surface):
        pygame.draw.rect(surface,config.COLOR_BG_LIGHT,self.rect,border_radius=8)
        pygame.draw.rect(surface,config.COLOR_TABLE_EDGE,self.rect,2,border_radius=8)
        draw_text(surface,f"{self.label}: {self.value}  ›",self.rect.center,22)
