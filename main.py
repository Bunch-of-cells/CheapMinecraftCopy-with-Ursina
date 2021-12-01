"""My version of Minecraft"""

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from math import sqrt


class Voxel(Button):
    """Creates a voxel(block)\n
    position: The (x, y, z) coordinates of the block\n
    block: grass, stone, brick, dirt, etc.\n
    tag: unbreakable, decayable, gravity_affected, etc.
    kwargs: decay_into, etc."""

    voxels = dict()
    sound = None

    def __init__(
        self, position: tuple[int, int, int], block: str, tag: tuple = None, **kwargs
    ) -> None:
        self.block = block
        self.pos = position
        self.kwargs = Block.blocks[self.block].kwargs | kwargs

        if tag and "overwrite" in tag:
            self.tag = list(tag)
            self.tag.remove("overwrite")
        else:
            self.tag = Block.blocks[self.block].tag.copy()
            if type(tag) == str and tag not in self.tag:
                self.tag.append(tag)
            elif tag is not None:
                self.tag.extend(tag)

        super().__init__(
            parent=scene,
            position=position,
            model=Block.blocks[self.block].model,
            origin_y=0.5,
            texture=Block.blocks[block].texture,
            color=color.color(0, 0, random.uniform(0.9, 1)),
            scale=0.5,
        )
        Voxel.voxels[position] = self

    @property
    def pos(self) -> tuple[int, int, int]:
        return self.x, self.y, self.z

    @pos.setter
    def pos(self, value: tuple[int, int, int]) -> None:
        del Voxel.voxels[self.pos]
        self.set_position(value)
        Voxel.voxels[self.pos] = self

    def input(self, key: str) -> None:
        if self.hovered:
            if key == "right mouse down":
                self.break_block()
            elif key == "left mouse down":
                self.place_block()
            elif key == "middle mouse down":
                Hand.change(self.block)

    def decay(self, into=None) -> None:
        if into is None:
            into = Voxel(self.pos, self.kwargs["decay_into"])
        else:
            into = Voxel(self.pos, into)
        Voxel.voxels[self.pos] = into
        self.up2date(False)
        destroy(self)
        del self

    def place_block(self) -> None:
        a = self.position + mouse.normal
        newpos = (a.x, a.y, a.z)
        hand = Block.blocks[Hand.block]
        if Voxel.voxels.get(newpos) is None:
            if Hand.prev == "place" and Hand.block != "place":
                Hand.prev = Hand.block
                for block in self.neighbors(
                    Block.blocks["place"].kwargs["radius"], newpos
                ):
                    block.place_block()

            if "explosive" in hand.tag:
                for block in self.neighbors(hand.kwargs["radius"], newpos):
                    block.blow_block(newpos, hand.kwargs["damage"])

            if "implacable" not in hand.tag:
                new = Voxel(newpos, Hand.block)
                new.up2date()
                Voxel.sound.play()

            if Hand.block == "dirt":
                for block in new.neighbors(1, newpos):
                    if block.block == "grass":
                        new.decay("grass")

            Hand.prev = Hand.block

    def blow_block(self, blast_coords: tuple[int, int, int], damage: float) -> None:
        if "unbreakable" not in self.tag and "tnt-resistant" not in self.tag:
            res = self.kwargs.get("tnt_resistance")
            if res is None:
                res = 0
            dist = sqrt(
                (self.x - blast_coords[0]) ** 2
                + (self.y - blast_coords[1]) ** 2
                + (self.z - blast_coords[2]) ** 2
            )

            # adict = (self.x-blast_coords[0],self.y-blast_coords[1],self.z-blast_coords[2])
            # xdiff = int(abs(self.x-blast_coords[0]+0.5)/(self.x-blast_coords[0]+0.5))
            # ydiff = int(abs(self.x-blast_coords[1]+0.5)/(self.x-blast_coords[1]+0.5))
            # zdiff = int(abs(self.x-blast_coords[2]+0.5)/(self.x-blast_coords[2]+0.5))
            # a = max(adict)
            # if a == self.x-blast_coords[0]:posi = (self.x+xdiff,self.y,self.z)
            # elif a == self.y-blast_coords[1]:posi = (self.x,self.y+ydiff,self.z)
            # elif a == self.z-blast_coords[2]:posi = (self.x,self.y,self.z+zdiff)

            # prev = Voxel.voxels.get(posi)
            # if prev is not None:
            #     prev_res = prev.kwargs.get("tnt_resistance")
            #     if prev_res is None:prev_res = 0
            # else:prev_res=0

            toughness = dist / 10 + res
            if toughness < damage:
                Voxel.sound.play()
                del Voxel.voxels[self.pos]
                self.up2date(False)
                destroy(self)
                del self

    def break_block(self):
        if "unbreakable" not in self.tag:
            Voxel.sound.play()
            if Voxel.voxels.get(self.pos) is not None:
                del Voxel.voxels[self.pos]
            self.up2date(False)
            destroy(self)
            del self

    def fall(self) -> None:
        oldy = self.y
        x, y, z = self.pos

        while (
            Voxel.voxels.get((x, y - 1, z)) is None
            and sqrt(x ** 2 + y ** 2 + z ** 2) < World.world_size / 2 - 1
        ):
            y -= 1

        self.pos = (x, y, z)

        if oldy != y:
            if (top := Voxel.voxels.get((x, oldy + 1, z))) is not None:
                Voxel.up2date(top)
            self.up2date(False, ("bottom"))

    def up2date(self, checkself: bool = True, checkdir: tuple[str] = None) -> None:
        if checkdir is None:
            checkdir = ("left", "right", "top", "bottom", "front", "back")
        if "top" in checkdir and (
            top := Voxel.voxels.get((self.x, self.y + 1, self.z))
        ):
            if "gravity_affected" in top.tag:
                top.fall()

        if "left" in checkdir and (
            left := Voxel.voxels.get((self.x - 1, self.y, self.z))
        ):
            if "gravity_affected" in left.tag:
                left.fall()

        if "right" in checkdir and (
            right := Voxel.voxels.get((self.x + 1, self.y, self.z))
        ):
            if "gravity_affected" in right.tag:
                right.fall()

        if "bottom" in checkdir and (
            bottom := Voxel.voxels.get((self.x, self.y - 1, self.z))
        ):
            if "gravity_affected" in bottom.tag:
                bottom.fall()
            if "decayable" in bottom.tag:
                bottom.decay()

        if "front" in checkdir and (
            front := Voxel.voxels.get((self.x, self.y, self.z + 1))
        ):
            if "gravity_affected" in front.tag:
                front.fall()

        if "back" in checkdir and (
            back := Voxel.voxels.get((self.x, self.y, self.z - 1))
        ):
            if "gravity_affected" in back.tag:
                back.fall()

        if checkself:
            if "gravity_affected" in self.tag:
                self.fall()

    @staticmethod
    def generate() -> None:
        Sky()
        xa = int(
            abs(World.end[0] - World.origin[0] + 0.5)
            / (World.end[0] - World.origin[0] + 0.5)
        )
        ya = int(
            abs(World.end[1] - World.origin[1] + 0.5)
            / (World.end[1] - World.origin[1] + 0.5)
        )
        za = int(
            abs(World.end[2] - World.origin[2] + 0.5)
            / (World.end[2] - World.origin[2] + 0.5)
        )
        for x in range(World.origin[0], World.end[0] + xa, xa):
            for y in range(World.origin[1], World.end[1] + ya, ya):
                for z in range(World.origin[2], World.end[2] + za, za):
                    if (x, y, z) == World.spawn:
                        Voxel((x, y, z), "stone", ("unbreakable", "overwrite"))
                    elif y == World.origin[1]:
                        Voxel((x, y, z), "grass")
                    elif y == World.end[1]:
                        Voxel((x, y, z), "stone", tag=("unbreakable"))
                    elif y > ((World.end[1] + World.origin[1]) / 2):
                        Voxel((x, y, z), "dirt")
                    else:
                        Voxel((x, y, z), "stone")

    @staticmethod
    def neighbors(radius: int, pos: tuple[int, int, int]) -> tuple[int, int, int]:
        for x in range(-radius, radius + 1):
            for y in range(-radius, radius + 1):
                for z in range(-radius, radius + 1):
                    if (
                        block := Voxel.voxels.get((x + pos[0], y + pos[1], z + pos[2]))
                    ) :
                        if (
                            sqrt(
                                (block.x - pos[0]) ** 2
                                + (block.y - pos[1]) ** 2
                                + (block.z - pos[2]) ** 2
                            )
                            <= radius
                        ):
                            yield block


class Sky(Entity):
    """Sky of the world"""

    def __init__(self) -> None:
        super().__init__(
            parent=scene,
            model="sphere",
            texture=load_texture("assets/skybox.png"),
            scale=World.world_size,
            double_sided=True,
            x=World.spawn[0],
            y=World.spawn[1],
            z=World.spawn[2],
        )


class Hand:
    """The Hand.hand of the player"""

    def __init__(self, block: str = "grass") -> None:
        Hand.block = block
        Hand.prev = block
        Hand.hand = Entity(
            parent=camera.ui,
            model="assets/arm",
            texture=load_texture("assets/arm_texture.png"),
            scale=0.2,
            rotation=Vec3(150, -10, 0),
            position=Vec2(0.4, -0.6),
        )

        Hand.hold = Entity(
            parent=camera.ui,
            model="assets/block",
            texture=Block.blocks[self.block].texture,
            scale=0.05,
            position=(0.8, 0.42),
        )

        Hand.hold_border = Entity(
            parent=camera.ui,
            model="quad",
            texture="assets/border.png",
            scale=0.1,
            position=(0.8, 0.42),
        )

        Hand.fps = Text(text="", origin=(9, -17), color=color.black)

        Hand.text = Text(text="", origin=(0, -17), color=color.black)

    @staticmethod
    def active() -> None:
        Hand.hand.position = Vec2(0.3, -0.5)

    @staticmethod
    def passive() -> None:
        Hand.hand.position = Vec2(0.4, -0.6)

    @staticmethod
    def change(block: str) -> None:
        Hand.block = block
        Hand.hold.texture = Block.blocks[Hand.block].texture


class Block:
    """Blocks"""

    blocks = {}

    def __init__(
        self,
        block: str,
        texture: str,
        key: str,
        loaded: bool = False,
        model: str = None,
        tag: tuple = None,
        **kwargs,
    ) -> None:

        if loaded:
            self.texture = texture
        else:
            self.texture = load_texture(texture)

        if type(tag) == str:
            self.tag = [tag]
        elif tag is not None:
            self.tag = list(tag)
        else:
            self.tag = []

        self.kwargs = kwargs
        self.block = block
        self.key = key
        if model is None:
            self.model = "assets/block"
        else:
            self.model = model
        Block.blocks[self.block] = self


class Player(FirstPersonController):
    """Player"""

    def __init__(self, hand=None, **kwargs) -> None:
        Hand(hand)
        super().__init__(**kwargs)
        Player.player = self


class World:
    spawn: tuple[int, int, int]
    origin: tuple[int, int, int]
    end: tuple[int, int, int]
    world_size: int

    def __init__(self, spawn, origin, end, world_size) -> None:
        World.spawn = spawn
        World.origin = origin
        World.end = end
        World.world_size = world_size
        World.validate_coords()

    @staticmethod
    def validate_coords() -> None:
        if not (
            isinstance(World.origin[0], int)
            and isinstance(World.origin[1], int)
            and isinstance(World.origin[2], int)
        ):
            raise Exception("Origin coordinates must be integers")
        if not (
            isinstance(World.spawn[0], int)
            and isinstance(World.spawn[1], int)
            and isinstance(World.spawn[2], int)
        ):
            raise Exception("Spawn coordinates must be integers")
        if not (
            isinstance(World.end[0], int)
            and isinstance(World.end[1], int)
            and isinstance(World.end[2], int)
        ):
            raise Exception("End coordinates must be integers")
        if not (
            -World.world_size / 2 < World.origin[0] < World.world_size / 2
            and World.end[0] < World.world_size / 2
        ):
            raise Exception("x: origin and end have to be inside the world")
        if not (
            -World.world_size / 2 < World.origin[1] < World.world_size / 2
            and World.end[1] < World.world_size / 2
        ):
            raise Exception("y: origin and end have to be inside the world")
        if not (
            -World.world_size / 2 < World.origin[2] < World.world_size / 2
            and World.end[2] < World.world_size / 2
        ):
            raise Exception("z: origin and end have to be inside the world")
        if World.origin[0] < World.end[0]:
            raise Exception("Origin x cannot be less than End x")
        if World.origin[1] < World.end[1]:
            raise Exception("Origin y cannot be less than End y")
        if World.origin[2] < World.end[2]:
            raise Exception("Origin z cannot be less than End z")
        if not (World.origin[0] >= World.spawn[0] >= World.end[0]):
            raise Exception("Spawn x has to be between Origin x and End x")
        if not (World.origin[1] >= World.spawn[1] >= World.end[1]):
            raise Exception("Spawn y has to be between Origin y and End y")
        if not (World.origin[2] >= World.spawn[2] >= World.end[2]):
            raise Exception("Spawn z has to be between Origin z and End z")


def update() -> None:
    """Updates the game"""

    Hand.text.text = f"X:{round(Player.player.x,2)} Y:{round(Player.player.y,2)} Z:{round(Player.player.z,2)}"

    ppos = sqrt((Player.player.x ** 2 + Player.player.y ** 2 + Player.player.z ** 2))

    if ppos >= World.world_size / 2:
        Player.player.set_position(World.spawn)

    if held_keys["left mouse"] or held_keys["right mouse"]:
        Hand.active()
    else:
        Hand.passive()

    for block, bl in Block.blocks.items():
        if held_keys[bl.key]:
            Hand.change(block)
            break
    if held_keys["escape"]:
        application.quit()


def main() -> None:
    """Main function"""
    World((0, 0, 0), (20, 0, 20), (-20, -2, -20), 150)

    app = Ursina()
    window.fps_counter.enabled = False
    window.exit_button.visible = False
    window.size = window.fullscreen_size

    Voxel.sound = Audio("assets/punch_sound", loop=False, autoplay=False)

    # 3**(1/2) / 10 = 0.173205081
    Block(
        "grass",
        "assets/grass_block.png",
        "1",
        tag=("decayable", "gravity_affected"),
        decay_into="dirt",
    )
    Block("stone", "assets/stone_block.png", "2", tag="gravity_affected")
    Block("brick", "assets/brick_block.png", "3")
    Block("dirt", "assets/dirt_block.png", "4", tag="gravity_affected")
    Block(
        "tnt",
        "white_cube",
        "5",
        True,
        tag=("implacable", "explosive"),
        radius=10,
        damage=1,
    )
    Block("place", "brick", "6", True, radius=7)
    Block(
        "noise",
        "noise",
        "7",
        True,
        tag=("explosive", "unbreakable"),
        radius=10,
        damage=1,
    )
    Block("nontnt", "grass", "8", True, tnt_resistance=0.8)
    Block("glass", "assets/border.png", "9", model="cube")

    Voxel.generate()
    Player(
        "tnt",
        height=1,
        jump_height=1,
        jump_duration=0.3,
        x=World.spawn[0],
        y=World.spawn[1],
        z=World.spawn[2],
    )

    app.run()


if __name__ == "__main__":
    main()
