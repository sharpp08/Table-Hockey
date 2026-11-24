"""Small, reusable menu widgets for Table Hockey."""
import pygame
import config

def draw_text(surface, text, center, size=30, color=config.COLOR_TEXT, bold=False):
    font = pygame.font.Font(None, max(14, int(size)))
    font.set_bold(bool(bold))
    image = font.render(str(text), True, color)
    surface.blit(image, image.get_rect(center=center))
    return image.get_rect(center=center)

class Button:
    def __init__(self, rect, label, callback=None, accent=config.COLOR_P1):
        self.rect=pygame.Rect(rect); self.label=label; self.callback=callback
        self.accent=accent; self.hover=0.0; self.enabled=True
    def update(self, dt, mouse, focused=False):
        target=1.0 if self.enabled and (self.rect.collidepoint(mouse) or focused) else 0.0
        self.hover += (target-self.hover)*min(1.0,dt*13.0)
    def draw(self, surface):
        r=self.rect.copy()
        if self.hover: r.inflate_ip(int(5*self.hover),int(3*self.hover))
        bg=tuple(int(c*(.8+.35*self.hover)) for c in config.COLOR_BG_LIGHT)
        pygame.draw.rect(surface,bg,r,border_radius=10)
        pygame.draw.rect(surface,self.accent if self.hover>.15 else config.COLOR_TABLE_EDGE,r,2,border_radius=10)
        draw_text(surface,self.label,r.center,max(22,int(r.h*.48)),config.COLOR_WHITE if self.enabled else config.COLOR_TEXT_DIM)
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
