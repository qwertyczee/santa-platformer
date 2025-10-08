import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pygame

from constants import ASSETS_DIR, BASE_WIDTH, BASE_HEIGHT
from enemy import Enemy
from settings import Settings


DEFAULT_CAMPAIGN_PATH = ASSETS_DIR / "levels" / "story_campaign.json"


def _default_campaign() -> Dict:
    """Return a small fallback campaign used when the JSON fails to load."""
    return {
        "title": "Fallback Holiday",
        "description": "Default campaign used when the story JSON cannot be read.",
        "levels": [
            {
                "id": "fallback_village",
                "name": "Snowy Village",
                "width": 1600,
                "height": 600,
                "player_start": [80, 480],
                "goal": [1500, 480, 60, 80],
                "ground": [0, 560, 1600, 40],
                "platforms": [
                    [200, 430, 160, 20],
                    [420, 330, 160, 20],
                    [700, 460, 200, 20],
                    [1100, 380, 200, 20],
                    [1350, 300, 180, 20],
                ],
                "presents": [
                    [220, 400, 30, 30],
                    [460, 300, 30, 30],
                    [760, 430, 30, 30],
                    [1120, 350, 30, 30],
                    [1370, 270, 30, 30],
                ],
                "enemies": [
                    [600, 520, 40, 40, 500, 740, 2.0],
                    [1300, 340, 40, 40, 1250, 1450, 1.5],
                ],
                "powerups": [
                    {"rect": [520, 480, 24, 24], "type": "double_jump"},
                    {"rect": [900, 420, 24, 24], "type": "speed_boost"},
                ],
                "story": {
                    "intro": [
                        {
                            "speaker": "Narrator",
                            "portrait": None,
                            "speed": 30,
                            "text": "Welcome to the fallback story. Collect presents and reach the tree!",
                        }
                    ],
                    "outro": [
                        {
                            "speaker": "Narrator",
                            "portrait": None,
                            "speed": 30,
                            "text": "Well done!",
                        }
                    ],
                    "interludes": [],
                },
            }
        ],
    }


def load_campaign_data(path: Path = DEFAULT_CAMPAIGN_PATH) -> Dict:
    """Load campaign JSON data and validate the presence of the levels array."""
    campaign: Dict
    source_path = Path(path)
    try:
        with source_path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        # Allow the JSON to either contain {"campaign": {...}} or the campaign directly.
        campaign = raw.get("campaign", raw)
        if not isinstance(campaign, dict):
            raise ValueError("Campaign root must be a JSON object")
        levels = campaign.get("levels")
        if not isinstance(levels, list) or not levels:
            raise ValueError("Campaign file must define a non-empty 'levels' array")
    except Exception as exc:
        print(f"[LevelManager] Failed to load campaign '{source_path}': {exc}")
        campaign = _default_campaign()
    return campaign


class LevelManager:
    """Load and manage levels defined in the JSON story campaign."""

    def __init__(
        self,
        campaign_data: Dict,
        settings: Optional[Settings] = None,
        index: int = 0,
    ) -> None:
        self.settings = settings if settings is not None else Settings.load()
        self.campaign = campaign_data
        self.levels: List[Dict] = campaign_data.get("levels", [])
        self.metadata = {k: v for k, v in campaign_data.items() if k != "levels"}
        self.index = max(0, min(index, len(self.levels) - 1)) if self.levels else 0

        # Runtime state fields initialised on load_level
        self.completed = False
        self.width = BASE_WIDTH
        self.height = BASE_HEIGHT
        self.ground = pygame.Rect(0, 0, self.width, 40)
        self.platforms: List[pygame.Rect] = []
        self.dynamic_platforms: List[pygame.Rect] = []
        self.presents: List[Dict] = []
        self.powerups: List[Dict] = []
        self.enemies: List[Enemy] = []
        self.checkpoints: List[Dict] = []
        self.story_intro: List[Dict] = []
        self.story_outro: List[Dict] = []
        self.story_interludes: Dict[str, List[Dict]] = {}
        self.story_registry: Dict[str, List[Dict]] = {}
        self.goal = pygame.Rect(0, 0, 0, 0)
        self.player_start: Tuple[int, int] = (0, 0)
        self.total_presents = 0
        self.name = ""
        self.background: Optional[pygame.Surface] = None
        self.overlay: Optional[pygame.Surface] = None
        self.parallax_layers: List[Dict] = []
        self.decorations: List[Dict] = []
        self.events: List[Dict] = []
        self.respawn_point: Tuple[int, int] = (0, 0)
        self.outro_played = False

        if self.levels:
            self.load_level(self.index)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def get_level_names(self) -> List[str]:
        return [lvl.get("name", f"Level {idx + 1}") for idx, lvl in enumerate(self.levels)]

    def _load_background(self, data: Dict) -> pygame.Surface:
        bg_info = data.get("background", {}) if isinstance(data.get("background"), dict) else {}
        fallback_color = tuple(bg_info.get("ambientColor", [50, 50, 100]))

        bg_name = bg_info.get("image")
        if bg_name:
            bg_path = ASSETS_DIR / bg_name
        else:
            bg_path = ASSETS_DIR / f"bckg{self.index + 1}.png"

        surface = pygame.Surface((self.width, self.height))
        surface.fill(fallback_color if len(fallback_color) >= 3 else (50, 50, 100))
        if bg_path.exists():
            try:
                bg_img = pygame.image.load(str(bg_path)).convert()
                surface.blit(pygame.transform.scale(bg_img, (self.width, self.height)), (0, 0))
            except pygame.error as exc:  # pragma: no cover - depends on pygame surface
                print(f"[LevelManager] Failed to load background {bg_path}: {exc}")
        self.parallax_layers = bg_info.get("parallaxLayers", [])
        return surface

    def _parse_events(self, events: List[Dict]) -> List[Dict]:
        parsed = []
        for item in events or []:
            trigger = item.get("trigger", "")
            if ":" in trigger:
                trigger_type, trigger_value = trigger.split(":", 1)
            else:
                trigger_type, trigger_value = trigger, ""
            parsed.append(
                {
                    **item,
                    "trigger_type": trigger_type,
                    "trigger_value": trigger_value,
                    "fired": False,
                }
            )
        return parsed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load_level(self, index: int) -> None:
        if not self.levels:
            return
        data = self.levels[index]
        self.index = index
        self.completed = False
        self.outro_played = False

        self.width = int(data.get("width", BASE_WIDTH))
        self.height = int(data.get("height", BASE_HEIGHT))

        ground_rect = data.get("ground", [0, self.height - 40, self.width, 40])
        self.ground = pygame.Rect(*ground_rect)

        self.platforms = [pygame.Rect(*p) for p in data.get("platforms", [])]
        self.dynamic_platforms = []

        # presents with randomized textures
        present_options = ["present", "present1", "present2", "present3"]
        self.presents = []
        for entry in data.get("presents", []):
            rect = pygame.Rect(*entry)
            texture = random.choice(present_options)
            self.presents.append({"rect": rect, "texture": texture})

        self.powerups = [
            {"rect": pygame.Rect(*p["rect"]), "type": p["type"]}
            for p in data.get("powerups", [])
            if "rect" in p and "type" in p
        ]

        self.enemies = [Enemy(*enemy_tuple) for enemy_tuple in data.get("enemies", [])]

        # apply difficulty scaling to enemy speed
        mult = getattr(self.settings, "enemy_speed_mult", 1.0)
        if mult not in (1.0, 1):
            for ent in self.enemies:
                ent.speed *= mult
                ent.vx = ent.speed if ent.vx >= 0 else -ent.speed

        sx, sy = data.get("player_start", [0, 0])
        gx, gy, gw, gh = data.get("goal", [0, 0, 0, 0])
        self.goal = pygame.Rect(gx, gy, gw, gh)
        self.player_start = (int(sx), int(sy))
        self.respawn_point = self.player_start
        self.total_presents = len(self.presents)
        self.name = data.get("name", f"Level {index + 1}")

        self.background = self._load_background(data)
        self.overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 120))

        # story sequences
        story = data.get("story", {}) if isinstance(data.get("story"), dict) else {}
        self.story_intro = story.get("intro", []) or []
        self.story_outro = story.get("outro", []) or []
        interludes = story.get("interludes", []) or []
        self.story_interludes = {item.get("id"): item.get("sequence", []) for item in interludes if item.get("id")}
        self.story_registry = {
            "intro": self.story_intro,
            "outro": self.story_outro,
            **self.story_interludes,
        }

        # checkpoints
        self.checkpoints = []
        for cp in data.get("checkpoints", []) or []:
            rect = pygame.Rect(*cp.get("rect", [0, 0, 0, 0]))
            respawn = cp.get("respawn", [self.player_start[0], self.player_start[1]])
            self.checkpoints.append(
                {
                    "id": cp.get("id", f"checkpoint_{len(self.checkpoints)}"),
                    "rect": rect,
                    "respawn": (int(respawn[0]), int(respawn[1])) if len(respawn) >= 2 else self.player_start,
                    "story": cp.get("story"),
                    "triggered": False,
                }
            )

        self.events = self._parse_events(data.get("events", []) or [])
        self.decorations = data.get("decorations", []) or []

    def activate_checkpoint(self, checkpoint_id: str) -> Optional[List[Dict]]:
        for checkpoint in self.checkpoints:
            if checkpoint["id"] == checkpoint_id and not checkpoint["triggered"]:
                checkpoint["triggered"] = True
                self.player_start = checkpoint["respawn"]
                self.respawn_point = self.player_start
                story_key = checkpoint.get("story")
                return self.story_interludes.get(story_key)
        return None

    def checkpoint_collisions(self, player_rect: pygame.Rect) -> Optional[Dict]:
        for checkpoint in self.checkpoints:
            if not checkpoint["triggered"] and player_rect.colliderect(checkpoint["rect"]):
                return checkpoint
        return None

    def handle_progress_event(self, trigger_type: str, value) -> List[Dict]:
        triggered: List[Dict] = []
        for event in self.events:
            if event["fired"]:
                continue
            if event["trigger_type"] != trigger_type:
                continue

            should_fire = False
            if trigger_type == "presents_collected":
                try:
                    target = int(event["trigger_value"])
                    should_fire = value >= target
                except ValueError:
                    should_fire = False
            elif trigger_type == "checkpoint_reached":
                should_fire = value == event["trigger_value"]
            else:
                should_fire = True

            if should_fire:
                event["fired"] = True
                triggered.append(event)
        return triggered

    def apply_event_effect(self, event: Dict) -> None:
        effect = event.get("effect")
        payload = event.get("payload", {})
        if effect == "spawn_powerup":
            rect = payload.get("rect")
            ptype = payload.get("type")
            if rect and ptype:
                self.powerups.append({"rect": pygame.Rect(*rect), "type": ptype})
        elif effect == "spawn_platforms":
            for plat in payload.get("platforms", []) or []:
                rect = pygame.Rect(*plat)
                self.platforms.append(rect)
                self.dynamic_platforms.append(rect)

    def get_story_sequence(self, key: str) -> List[Dict]:
        return self.story_registry.get(key, [])

    def next_level(self) -> bool:
        if self.index + 1 < len(self.levels):
            self.index += 1
            self.load_level(self.index)
            return True
        return False