"""生成 QTTrigrs 的图标资源（PNG，64x64，透明背景）。依赖 Pillow。"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / "icons"
OUT.mkdir(parents=True, exist_ok=True)


def new_canvas(size=64, bg=(0, 0, 0, 0)):
    img = Image.new("RGBA", (size, size), bg)
    return img, ImageDraw.Draw(img)


def save(img, name):
    img.save(OUT / name)
    print("saved", name)


# 1) app.png —— 绿色山体 + 白色积雪
img, d = new_canvas()
d.polygon([(6, 54), (32, 12), (58, 54)], fill=(46, 139, 87, 255))
d.polygon([(22, 54), (32, 30), (42, 54)], fill=(255, 255, 255, 255))
d.rectangle([6, 52, 58, 58], fill=(34, 94, 60, 255))
save(img, "app.png")

# 2) new.png —— 白纸 + 折角
img, d = new_canvas()
d.rectangle([14, 10, 48, 54], fill=(250, 250, 250, 255), outline=(90, 90, 90, 255), width=3)
d.polygon([(40, 10), (48, 18), (40, 18)], fill=(180, 180, 180, 255))
save(img, "new.png")

# 3) open.png —— 黄色文件夹
img, d = new_canvas()
d.rounded_rectangle([8, 16, 56, 50], radius=4, fill=(240, 190, 60, 255))
d.rectangle([8, 16, 32, 26], fill=(210, 160, 40, 255))
save(img, "open.png")

# 4) save.png —— 蓝色软盘
img, d = new_canvas()
d.rounded_rectangle([10, 10, 54, 54], radius=4, fill=(60, 120, 210, 255))
d.rectangle([20, 10, 44, 30], fill=(235, 235, 235, 255))
d.rectangle([16, 34, 48, 54], fill=(235, 235, 235, 255))
d.rectangle([38, 18, 44, 30], fill=(60, 120, 210, 255))
save(img, "save.png")

# 5) check.png —— 绿底白勾
img, d = new_canvas()
d.ellipse([6, 6, 58, 58], fill=(46, 160, 80, 255))
d.line([(18, 33), (28, 43), (47, 22)], fill=(255, 255, 255, 255), width=7, joint="curve")
save(img, "check.png")

# 6) run.png —— 绿底白色播放三角
img, d = new_canvas()
d.ellipse([6, 6, 58, 58], fill=(46, 160, 80, 255))
d.polygon([(26, 20), (26, 46), (47, 33)], fill=(255, 255, 255, 255))
save(img, "run.png")

# 7) stop.png —— 红底白色方块
img, d = new_canvas()
d.ellipse([6, 6, 58, 58], fill=(200, 60, 60, 255))
d.rectangle([22, 22, 42, 42], fill=(255, 255, 255, 255))
save(img, "stop.png")

# 8) preview.png —— 蓝色眼睛
img, d = new_canvas()
d.ellipse([6, 22, 58, 42], fill=(90, 150, 220, 255))
d.ellipse([22, 26, 42, 38], fill=(255, 255, 255, 255))
d.ellipse([29, 28, 35, 36], fill=(40, 60, 90, 255))
save(img, "preview.png")

# 9) trigrs.png —— 滑坡（棕色坡面 + 箭头）
img, d = new_canvas()
d.polygon([(8, 54), (30, 20), (56, 54)], fill=(170, 120, 70, 255))
d.line([(18, 40), (42, 40)], fill=(255, 255, 255, 255), width=5)
d.polygon([(38, 34), (48, 40), (38, 46)], fill=(255, 255, 255, 255))
save(img, "trigrs.png")

# 10) topoindex.png —— 蓝色栅格/流向
img, d = new_canvas()
d.rounded_rectangle([8, 8, 56, 56], radius=4, outline=(70, 130, 200, 255), width=4)
for x in (24, 40):
    d.line([(x, 8), (x, 56)], fill=(70, 130, 200, 255), width=2)
for y in (24, 40):
    d.line([(8, y), (56, y)], fill=(70, 130, 200, 255), width=2)
d.line([(14, 30), (22, 30), (22, 38), (30, 38)], fill=(240, 80, 60, 255), width=4, joint="curve")
save(img, "topoindex.png")


def _circle_check(color):
    img, d = new_canvas()
    d.ellipse([6, 6, 58, 58], fill=color)
    d.line([(18, 33), (28, 43), (47, 22)], fill=(255, 255, 255, 255), width=7, joint="curve")
    return img


def _circle_play(color):
    img, d = new_canvas()
    d.ellipse([6, 6, 58, 58], fill=color)
    d.polygon([(26, 20), (26, 46), (47, 33)], fill=(255, 255, 255, 255))
    return img


# 检查参数（区分 TRIGRS 绿 / TopoIndex 蓝）
save(_circle_check((46, 160, 80, 255)), "check_trigrs.png")
save(_circle_check((70, 130, 200, 255)), "check_topo.png")

# 运行（区分 TRIGRS 绿 / TopoIndex 蓝）
save(_circle_play((46, 160, 80, 255)), "run_trigrs.png")
save(_circle_play((70, 130, 200, 255)), "run_topo.png")

# 输入预览 —— 文档 + 文本行
img, d = new_canvas()
d.rounded_rectangle([12, 8, 52, 56], radius=3, fill=(250, 250, 250, 255), outline=(90, 90, 90, 255), width=3)
for y in (20, 28, 36, 44):
    d.line([(20, y), (44, y)], fill=(120, 140, 170, 255), width=3)
save(img, "preview_input.png")

# 结果预览 —— 柱状图
img, d = new_canvas()
d.rectangle([10, 44, 54, 54], fill=(160, 160, 160, 255))
for x, h in ((14, 26), (26, 36), (38, 18), (46, 30)):
    d.rectangle([x, 54 - h, x + 6, 54], fill=(46, 160, 80, 255))
save(img, "preview_result.png")

# 浏览文件 —— 黄色文件夹 + 箭头
img, d = new_canvas()
d.rounded_rectangle([6, 14, 46, 50], radius=4, fill=(240, 190, 60, 255))
d.rectangle([6, 14, 26, 24], fill=(210, 160, 40, 255))
d.line([(34, 28), (52, 34)], fill=(60, 90, 140, 255), width=4)
d.polygon([(46, 26), (56, 34), (46, 42)], fill=(60, 90, 140, 255))
save(img, "browse.png")

print("done:", OUT)
