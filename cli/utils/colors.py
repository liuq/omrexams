def alpha(color, alpha):
    return (*color[:3], 255 * alpha)

# Colors are usually coded in BGR within openCV

RED = (0, 0, 255, 255)
GREEN = (0, 255, 0, 255)
BLUE = (255, 0, 0, 255)
MAGENTA = (255, 0, 255, 255)
CYAN = (255, 255, 0, 255)
YELLOW = (0, 255, 255, 255)
ORANGE = (0, 102, 255, 255)
GRAY = (127, 127, 127, 255)
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)