from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import hashlib


Color = Tuple[int, int, int]


@dataclass(frozen=True)
class SceneSpec:
    family: str
    variant: str
    palette: Dict[str, Color]
    label: str
    overlay: Dict[str, str] = field(default_factory=dict)
    venue_scale: str = "none"
    crowd_mode: str = "none"
    crowd_intensity: float = 0.0
    transport_prestige: int = 0
    housing_status: int = 0
    work_prestige: int = 0
    style_variant: str = "base"
    continuity_key: str = "default"
    readability_overlay_alpha_top: int = 70
    readability_overlay_alpha_bottom: int = 85


class SceneBackdropRenderer:
    """State-driven, read-only backdrop renderer.

    Selects and draws lightweight illustrative backdrops from UI shell state
    (plus optional derived world state), without changing simulation state.
    """

    PALETTE_SETS: Dict[str, Tuple[Dict[str, Color], ...]] = {
        "home": (
            {"sky": (92, 130, 180), "ground": (60, 82, 58), "main": (170, 160, 148), "accent": (96, 76, 62), "trim": (220, 210, 190)},
            {"sky": (104, 136, 176), "ground": (62, 78, 60), "main": (178, 170, 156), "accent": (110, 88, 66), "trim": (232, 224, 210)},
            {"sky": (88, 124, 164), "ground": (64, 74, 62), "main": (160, 154, 146), "accent": (86, 68, 58), "trim": (210, 202, 186)},
        ),
        "transit": (
            {"sky": (100, 136, 178), "ground": (72, 74, 80), "main": (76, 94, 114), "accent": (210, 210, 210), "trim": (250, 230, 120)},
            {"sky": (104, 142, 184), "ground": (68, 72, 82), "main": (84, 102, 126), "accent": (220, 220, 220), "trim": (255, 236, 138)},
            {"sky": (90, 130, 170), "ground": (66, 68, 76), "main": (72, 90, 110), "accent": (200, 204, 210), "trim": (242, 220, 112)},
        ),
        "work": (
            {"sky": (84, 110, 148), "ground": (50, 54, 62), "main": (112, 106, 118), "accent": (196, 122, 86), "trim": (224, 216, 208)},
            {"sky": (90, 116, 156), "ground": (46, 52, 64), "main": (118, 108, 126), "accent": (210, 132, 92), "trim": (232, 220, 210)},
            {"sky": (78, 104, 144), "ground": (48, 52, 58), "main": (106, 100, 112), "accent": (184, 118, 84), "trim": (214, 206, 198)},
        ),
        "public": (
            {"sky": (96, 126, 160), "ground": (68, 70, 78), "main": (134, 128, 118), "accent": (180, 150, 106), "trim": (220, 212, 198)},
            {"sky": (102, 132, 166), "ground": (66, 70, 80), "main": (140, 132, 122), "accent": (190, 156, 112), "trim": (228, 218, 202)},
            {"sky": (90, 120, 154), "ground": (64, 68, 76), "main": (126, 122, 114), "accent": (172, 144, 102), "trim": (212, 204, 192)},
        ),
    }

    def build_spec(self, ui_shell_state: Dict, world_state: Optional[Dict] = None) -> SceneSpec:
        world_state = dict(world_state or {})
        top = dict(ui_shell_state.get("top_context", {}) or {})
        scene = dict(ui_shell_state.get("scene", {}) or {})

        state = str(top.get("state", "grounded"))
        headline = str(top.get("headline", ""))
        tags = [str(t) for t in (top.get("tags") or [])]

        if state == "in_transit" or scene.get("transit"):
            family = "transit"
            variant = self._select_transit_variant(scene, headline, tags, world_state)
        elif self._is_work_scene(headline):
            family = "work"
            variant = self._select_work_variant(headline, world_state)
        elif self._is_home_scene(headline):
            family = "home"
            variant = self._select_home_variant(tags, world_state)
        else:
            family = "public"
            variant = self._select_public_variant(headline)

        continuity_key = self._continuity_key(family, variant, ui_shell_state, world_state)
        style = self._style_for(continuity_key)
        palette = self._palette_for(family, variant, top, continuity_key, style, world_state)
        label = self._label_for(family, variant)
        overlay = self._overlay(top, scene, family, variant)
        venue_scale = self._venue_scale_for(family, variant)
        crowd_intensity = self._crowd_intensity(family, variant, world_state)
        crowd_mode = self._crowd_mode_for(crowd_intensity, venue_scale)
        transport_prestige = self._transport_prestige(variant) if family == "transit" else 0
        housing_status = self._housing_status(variant) if family == "home" else 0
        work_prestige = self._work_prestige(variant) if family == "work" else 0
        return SceneSpec(
            family=family,
            variant=variant,
            palette=palette,
            label=label,
            overlay=overlay,
            venue_scale=venue_scale,
            crowd_mode=crowd_mode,
            crowd_intensity=crowd_intensity,
            transport_prestige=transport_prestige,
            housing_status=housing_status,
            work_prestige=work_prestige,
            style_variant=style["id"],
            continuity_key=continuity_key,
            readability_overlay_alpha_top=74,
            readability_overlay_alpha_bottom=92,
        )

    def draw(self, surface, spec: SceneSpec, rect, tick: int = 0):
        """Draw backdrop scene into rect. `surface` is a pygame surface."""
        import pygame

        x, y, w, h = rect
        sky_h = int(h * 0.62)

        pygame.draw.rect(surface, spec.palette["sky"], (x, y, w, sky_h))
        pygame.draw.rect(surface, spec.palette["ground"], (x, y + sky_h, w, h - sky_h))

        if spec.family == "home":
            self._draw_home(surface, spec, rect)
        elif spec.family == "transit":
            self._draw_transit(surface, spec, rect, tick=tick)
        elif spec.family == "work":
            self._draw_work(surface, spec, rect, tick=tick)
        else:
            self._draw_public(surface, spec, rect)

        # Top/bottom fades protect shell readability under all scene tints.
        fade = pygame.Surface((w, 60))
        fade.set_alpha(spec.readability_overlay_alpha_top)
        fade.fill((0, 0, 0))
        surface.blit(fade, (x, y))
        fade_bottom = pygame.Surface((w, int(h * 0.22)))
        fade_bottom.set_alpha(spec.readability_overlay_alpha_bottom)
        fade_bottom.fill((0, 0, 0))
        surface.blit(fade_bottom, (x, y + int(h * 0.78)))

    def _draw_home(self, surface, spec: SceneSpec, rect):
        import pygame

        x, y, w, h = rect
        bx = x + int(w * 0.28)
        by = y + int(h * 0.42)
        bw = int(w * 0.44)
        bh = int(h * 0.32)

        if spec.variant == "rough_start":
            pygame.draw.polygon(surface, spec.palette["main"], [(bx, by + bh), (bx + bw // 2, by), (bx + bw, by + bh)])
            pygame.draw.line(surface, spec.palette["trim"], (bx + bw // 2, by), (bx + bw // 2, by + bh), 2)
        else:
            # upscale silhouette by status
            boost = max(0, spec.housing_status - 2)
            bw += boost * 12
            bh += boost * 8
            pygame.draw.rect(surface, spec.palette["main"], (bx, by, bw, bh))
            roof_peak = int(h * (0.11 + style_shift(spec.style_variant) * 0.01))
            roof_pts = [(bx - 20, by), (bx + bw // 2, by - roof_peak), (bx + bw + 20, by)]
            pygame.draw.polygon(surface, spec.palette["accent"], roof_pts)
            window_offset = style_shift(spec.style_variant) * 2
            pygame.draw.rect(surface, spec.palette["trim"], (bx + int(bw * 0.08) + window_offset, by + int(bh * 0.2), 28, 28))
            pygame.draw.rect(surface, spec.palette["trim"], (bx + int(bw * 0.76) - window_offset, by + int(bh * 0.2), 28, 28))
            pygame.draw.rect(surface, (92, 64, 42), (bx + int(bw * 0.44), by + int(bh * 0.48), 34, int(bh * 0.52)))
            if spec.housing_status >= 4:
                pygame.draw.rect(surface, (44, 62, 38), (bx - 30, by + bh - 6, 20, 12), border_radius=6)
                pygame.draw.rect(surface, (44, 62, 38), (bx + bw + 10, by + bh - 6, 20, 12), border_radius=6)
            if spec.housing_status >= 5:
                pygame.draw.rect(surface, (54, 56, 64), (bx + bw + 30, by + bh + 8, 90, 24), border_radius=8)
                pygame.draw.rect(surface, spec.palette["trim"], (bx + bw + 56, by + bh + 6, 32, 12), border_radius=5)

    def _draw_transit(self, surface, spec: SceneSpec, rect, tick: int = 0):
        import pygame

        x, y, w, h = rect
        road_y = y + int(h * 0.67)
        pygame.draw.rect(surface, (54, 56, 64), (x, road_y, w, int(h * 0.19)))
        offset = (tick // 4) % 52
        for i in range(10):
            sx = x + i * int(w / 10)
            pygame.draw.rect(surface, (230, 222, 172), (sx + 8, road_y + int(h * 0.08), 34, 4))
        # motion feel
        pygame.draw.rect(surface, (230, 222, 172), (x + offset, road_y + int(h * 0.08), 42, 4))

        vx = x + int(w * 0.45)
        vy = road_y - 30
        if spec.variant in {"walking", "bike"}:
            pygame.draw.circle(surface, spec.palette["main"], (vx, vy), 12)
            pygame.draw.line(surface, spec.palette["main"], (vx, vy + 12), (vx, vy + 42), 4)
            if spec.variant == "bike":
                pygame.draw.circle(surface, spec.palette["trim"], (vx - 24, vy + 50), 12, 2)
                pygame.draw.circle(surface, spec.palette["trim"], (vx + 24, vy + 50), 12, 2)
                pygame.draw.line(surface, spec.palette["trim"], (vx - 24, vy + 50), (vx + 8, vy + 34), 2)
        elif spec.variant in {"cheap_car", "nicer_car", "limo"}:
            body_w = 88 if spec.variant == "cheap_car" else 106 if spec.variant == "nicer_car" else 165
            pygame.draw.rect(surface, spec.palette["main"], (vx - body_w // 2, vy + 20, body_w, 26), border_radius=8)
            pygame.draw.rect(surface, spec.palette["accent"], (vx - body_w // 4, vy + 8, body_w // 2, 16), border_radius=6)
            if spec.variant == "nicer_car":
                pygame.draw.rect(surface, spec.palette["trim"], (vx - body_w // 3, vy + 24, body_w // 6, 5), border_radius=2)
            if spec.variant == "limo":
                pygame.draw.rect(surface, spec.palette["trim"], (vx - body_w // 3, vy + 12, body_w // 2, 8), border_radius=3)
            pygame.draw.circle(surface, (22, 24, 28), (vx - body_w // 3, vy + 48), 10)
            pygame.draw.circle(surface, (22, 24, 28), (vx + body_w // 3, vy + 48), 10)
        else:  # planes
            plane_w = 176 if spec.variant == "commercial_plane" else 206
            plane_h = 42 if spec.variant == "commercial_plane" else 48
            pygame.draw.ellipse(surface, spec.palette["main"], (vx - plane_w // 2, y + int(h * 0.24), plane_w, plane_h))
            pygame.draw.polygon(surface, spec.palette["accent"], [(vx + 45, y + int(h * 0.24)), (vx + 82, y + int(h * 0.2)), (vx + 58, y + int(h * 0.32))])
            pygame.draw.polygon(surface, spec.palette["trim"], [(vx - 8, y + int(h * 0.3)), (vx + 46, y + int(h * 0.37)), (vx - 2, y + int(h * 0.37))])
            if spec.variant == "private_jet":
                pygame.draw.rect(surface, spec.palette["trim"], (vx - 18, y + int(h * 0.27), 68, 5), border_radius=2)
                pygame.draw.circle(surface, spec.palette["accent"], (vx - 68, y + int(h * 0.34)), 5)

    def _draw_work(self, surface, spec: SceneSpec, rect, tick: int = 0):
        import pygame

        x, y, w, h = rect
        if spec.variant in {"cheap_studio", "pro_studio"}:
            bx = x + int(w * 0.2)
            by = y + int(h * 0.34)
            bw = int(w * 0.6)
            bh = int(h * 0.38)
            pygame.draw.rect(surface, spec.palette["main"], (bx, by, bw, bh), border_radius=6)
            pygame.draw.rect(surface, spec.palette["accent"], (bx + 18, by + 18, bw - 36, 26), border_radius=4)
            pygame.draw.rect(surface, spec.palette["trim"], (bx + 60, by + 74, bw - 120, 72), border_radius=4)
            if spec.variant == "pro_studio":
                pygame.draw.rect(surface, spec.palette["trim"], (bx + bw - 110, by + 24, 72, 40), border_radius=4)
                pygame.draw.circle(surface, spec.palette["accent"], (bx + 36, by + bh - 24), 8)
        else:
            # stage/venue scale
            stage_scale = {
                "tiny_room": (0.24, 0.58, 0.48, 0.14, 2),
                "small_venue": (0.2, 0.57, 0.58, 0.16, 4),
                "medium_venue": (0.16, 0.55, 0.68, 0.18, 6),
                "large_venue": (0.12, 0.53, 0.76, 0.2, 8),
                "arena": (0.08, 0.5, 0.84, 0.23, 10),
                "stadium": (0.04, 0.46, 0.92, 0.26, 12),
            }
            sx, sy, sw, sh, cols = stage_scale.get(spec.variant, stage_scale["small_venue"])
            stage_y = y + int(h * sy)
            stage_x = x + int(w * sx)
            stage_w = int(w * sw)
            stage_h = int(h * sh)
            pygame.draw.rect(surface, spec.palette["main"], (stage_x, stage_y, stage_w, stage_h))
            # prestige cues
            if spec.work_prestige >= 3:
                pygame.draw.rect(surface, spec.palette["accent"], (stage_x + 20, stage_y - 18, stage_w - 40, 10))
            if spec.work_prestige >= 4:
                pygame.draw.rect(surface, spec.palette["trim"], (stage_x + int(stage_w * 0.28), stage_y - 40, int(stage_w * 0.44), 22))
            pulse = (tick // 8) % 2
            for i in range(cols):
                cx = stage_x + int(stage_w * 0.05) + i * int((stage_w * 0.9) / max(1, cols - 1))
                pygame.draw.circle(surface, spec.palette["accent"], (cx, y + int(h * 0.48)), 10)
                if spec.work_prestige >= 3:
                    beam_color = (spec.palette["trim"][0], spec.palette["trim"][1], spec.palette["trim"][2], 35)
                    beam = pygame.Surface((8, stage_y - (y + int(h * 0.49))), pygame.SRCALPHA)
                    beam.fill((beam_color[0], beam_color[1], beam_color[2], 18 + pulse * 12))
                    surface.blit(beam, (cx - 4, y + int(h * 0.49)))
            self._draw_crowd(surface, spec, rect)

    def _draw_public(self, surface, spec: SceneSpec, rect):
        import pygame

        x, y, w, h = rect
        pygame.draw.rect(surface, spec.palette["main"], (x + int(w * 0.14), y + int(h * 0.42), int(w * 0.24), int(h * 0.28)))
        pygame.draw.rect(surface, spec.palette["main"], (x + int(w * 0.42), y + int(h * 0.38), int(w * 0.44), int(h * 0.34)))
        pygame.draw.rect(surface, spec.palette["trim"], (x + int(w * 0.46), y + int(h * 0.44), int(w * 0.22), 24))

    def _is_home_scene(self, headline: str) -> bool:
        h = headline.lower()
        return any(k in h for k in ["home", "motel", "hotel", "room", "house", "apartment"])

    def _is_work_scene(self, headline: str) -> bool:
        h = headline.lower()
        return any(k in h for k in ["studio", "backstage", "venue", "stage", "label"])

    def _select_home_variant(self, tags, world_state: Dict) -> str:
        if "People Recognizing You" in tags and world_state.get("money", 0) >= 5000:
            return "luxury_house"
        if world_state.get("lodging_tier"):
            return str(world_state["lodging_tier"])
        money = world_state.get("money", 0)
        if money < 150:
            return "rough_start"
        if money < 900:
            return "apartment"
        if money < 4500:
            return "house"
        return "luxury_house"

    def _select_transit_variant(self, scene: Dict, headline: str, tags, world_state: Dict) -> str:
        mode = str(world_state.get("transport_mode", "")).lower()
        text = f"{headline} {' '.join(tags)}".lower()
        if mode:
            if "jet" in mode:
                return "private_jet"
            if "plane" in mode:
                return "commercial_plane"
            if "limo" in mode:
                return "limo"
            if "bike" in mode:
                return "bike"
            if mode in {"walk", "walking"}:
                return "walking"
            return "nicer_car" if world_state.get("money", 0) >= 2000 else "cheap_car"
        if "jet" in text:
            return "private_jet"
        if "plane" in text or "flight" in text:
            return "commercial_plane"
        if "bike" in text:
            return "bike"
        if "walk" in text:
            return "walking"
        return "cheap_car"

    def _select_work_variant(self, headline: str, world_state: Dict) -> str:
        h = headline.lower()
        if "studio" in h:
            return "pro_studio" if world_state.get("money", 0) >= 1800 else "cheap_studio"
        if "backstage" in h or "arena" in h:
            return "arena"
        fame = world_state.get("fame", 0)
        venue_tier = float(world_state.get("venue_tier", 0.0))
        if fame >= 280 or venue_tier >= 0.95:
            return "stadium"
        if fame >= 170 or venue_tier >= 0.78:
            return "arena"
        if fame >= 110 or venue_tier >= 0.62:
            return "large_venue"
        if fame >= 60 or venue_tier >= 0.46:
            return "medium_venue"
        if fame >= 24 or venue_tier >= 0.3:
            return "small_venue"
        return "tiny_room"

    def _select_public_variant(self, headline: str) -> str:
        h = headline.lower()
        if "airport" in h:
            return "airport"
        if "pawn" in h:
            return "pawn_shop"
        if "music" in h and "store" in h:
            return "music_store"
        return "street"

    def _palette_for(self, family: str, variant: str, top_context: Dict, continuity_key: str, style: Dict, world_state: Dict) -> Dict[str, Color]:
        sets = self.PALETTE_SETS.get(family, self.PALETTE_SETS["public"])
        base = dict(sets[self._stable_seed(continuity_key + family) % len(sets)])
        key = f"{family}:{variant}:{continuity_key}:{top_context.get('headline', '')}:{style.get('id')}"
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()

        shift = int(digest[:2], 16) % 18 - 9
        for k, color in base.items():
            base[k] = self._tint(color, shift)

        # mood progression by status: low tiers flatter, high tiers richer.
        status = max(
            self._housing_status(variant),
            self._work_prestige(variant),
            self._transport_prestige(variant),
            int(world_state.get("fame", 0) / 100),
        )
        richness = min(16, max(-8, (status - 2) * 3))
        base["accent"] = self._tint(base["accent"], richness)
        base["trim"] = self._tint(base["trim"], richness + 2)

        # day/night tint
        clock_text = str(top_context.get("clock", ""))
        if "PM" in clock_text and not any(t in clock_text for t in ["12:", "1:", "2:", "3:", "4:", "5:"]):
            for k, c in list(base.items()):
                base[k] = self._tint(c, -14)
        return base

    def _label_for(self, family: str, variant: str) -> str:
        readable = variant.replace("_", " ").title()
        if family == "transit":
            return f"Transit — {readable}"
        if family == "home":
            return f"Lodging — {readable}"
        if family == "work":
            return f"Work — {readable}"
        return f"Scene — {readable}"

    def _overlay(self, top: Dict, scene: Dict, family: str, variant: str) -> Dict[str, str]:
        overlay = {"title": str(top.get("headline", "")), "subtitle": self._label_for(family, variant)}
        if scene.get("transit"):
            transit = scene["transit"]
            overlay["destination"] = str(transit.get("destination") or "")
            overlay["remaining"] = str(transit.get("time_remaining") or "")
        return overlay

    def _venue_scale_for(self, family: str, variant: str) -> str:
        if family != "work":
            return "none"
        if variant in {"tiny_room", "cheap_studio"}:
            return "tiny"
        if variant in {"small_venue"}:
            return "small"
        if variant in {"medium_venue", "pro_studio"}:
            return "medium"
        if variant in {"large_venue"}:
            return "large"
        if variant in {"arena", "stadium"}:
            return "arena"
        return "small"

    def _crowd_intensity(self, family: str, variant: str, world_state: Dict) -> float:
        if family != "work" or variant in {"cheap_studio", "pro_studio"}:
            return 0.0
        visibility = float(world_state.get("public_visibility", 0.0))
        momentum = float(world_state.get("momentum", 0.0))
        buzz = float(world_state.get("recent_buzz", 0.0))
        base = min(1.0, (visibility / 22.0) + (buzz / 28.0) + (max(-1.0, momentum) + 1.0) * 0.18)
        if variant in {"arena", "stadium"}:
            base += 0.2
        elif variant in {"large_venue"}:
            base += 0.1
        return max(0.05, min(1.0, base))

    def _crowd_mode_for(self, intensity: float, venue_scale: str) -> str:
        if venue_scale == "none" or intensity <= 0:
            return "none"
        if intensity < 0.22:
            return "sparse_figures"
        if intensity < 0.45:
            return "grouped_silhouettes"
        if intensity < 0.72:
            return "dense_clusters"
        return "arena_bands"

    def _transport_prestige(self, variant: str) -> int:
        order = ["walking", "bike", "cheap_car", "nicer_car", "limo", "commercial_plane", "private_jet"]
        return max(0, order.index(variant) + 1) if variant in order else 0

    def _housing_status(self, variant: str) -> int:
        order = ["rough_start", "apartment", "house", "luxury_house"]
        return max(0, order.index(variant) + 1) if variant in order else 0

    def _work_prestige(self, variant: str) -> int:
        order = ["tiny_room", "small_venue", "medium_venue", "large_venue", "arena", "stadium", "cheap_studio", "pro_studio"]
        return max(1, order.index(variant) + 1) if variant in order else 1

    def _draw_crowd(self, surface, spec: SceneSpec, rect):
        import pygame

        if spec.crowd_mode == "none":
            return
        x, y, w, h = rect
        base_y = y + int(h * 0.76)
        color = self._tint(spec.palette["ground"], -18)
        if spec.crowd_mode == "sparse_figures":
            for i in range(8):
                cx = x + int(w * 0.2) + i * int(w * 0.07)
                pygame.draw.circle(surface, color, (cx, base_y), 5)
        elif spec.crowd_mode == "grouped_silhouettes":
            for i in range(14):
                cx = x + int(w * 0.14) + i * int(w * 0.055)
                pygame.draw.circle(surface, color, (cx, base_y), 6)
                pygame.draw.rect(surface, color, (cx - 4, base_y, 8, 8))
        elif spec.crowd_mode == "dense_clusters":
            for row in range(2):
                for i in range(20):
                    cx = x + int(w * 0.08) + i * int(w * 0.043)
                    cy = base_y - row * 10
                    pygame.draw.circle(surface, color, (cx, cy), 6)
        else:  # arena_bands
            pygame.draw.rect(surface, color, (x + int(w * 0.04), base_y - 8, int(w * 0.92), 18))
            pygame.draw.rect(surface, self._tint(color, -10), (x + int(w * 0.02), base_y + 14, int(w * 0.96), 14))
            for i in range(35):
                cx = x + int(w * 0.03) + i * int(w * 0.027)
                pygame.draw.circle(surface, self._tint(color, 8), (cx, base_y - 5), 3)

    def _continuity_key(self, family: str, variant: str, ui_shell_state: Dict, world_state: Dict) -> str:
        if family == "home":
            return str(world_state.get("home_key") or ui_shell_state.get("top_context", {}).get("headline", "home"))
        if family == "transit":
            return str(world_state.get("transport_key") or world_state.get("transport_mode") or variant)
        if family == "work":
            return str(world_state.get("work_key") or ui_shell_state.get("top_context", {}).get("headline", "work"))
        return str(world_state.get("public_key") or ui_shell_state.get("top_context", {}).get("headline", "public"))

    def _style_for(self, continuity_key: str) -> Dict[str, str]:
        seed = self._stable_seed(continuity_key)
        return {"id": f"v{seed % 5}", "seed": str(seed)}

    def _stable_seed(self, key: str) -> int:
        return int(hashlib.md5(key.encode("utf-8")).hexdigest()[:8], 16)

    def get_scene_audio_cues(self, spec: SceneSpec) -> Dict[str, str]:
        if spec.family == "work":
            crowd = {
                "sparse_figures": "crowd_murmur_low",
                "grouped_silhouettes": "crowd_murmur_medium",
                "dense_clusters": "crowd_applause",
                "arena_bands": "crowd_roar",
            }.get(spec.crowd_mode, "room_tone")
            return {"ambient": "venue_room_tone", "crowd": crowd, "energy": "stage_hum_high" if spec.work_prestige >= 4 else "stage_hum_low"}
        if spec.family == "transit":
            mapping = {
                "walking": "footsteps_ambient",
                "bike": "bike_wind",
                "cheap_car": "engine_hum_basic",
                "nicer_car": "engine_hum_clean",
                "limo": "engine_hum_luxury",
                "commercial_plane": "plane_cabin_ambience",
                "private_jet": "private_jet_ambience",
            }
            return {"ambient": mapping.get(spec.variant, "travel_ambience"), "crowd": "none", "energy": "movement_soft"}
        if spec.family == "home":
            return {"ambient": "quiet_room_ambience" if spec.housing_status >= 3 else "rough_room_ambience", "crowd": "none", "energy": "low"}
        return {"ambient": "street_ambience", "crowd": "none", "energy": "medium"}

    def _tint(self, color: Color, shift: int) -> Color:
        return (
            max(0, min(255, color[0] + shift)),
            max(0, min(255, color[1] + shift)),
            max(0, min(255, color[2] + shift)),
        )


def derive_world_visual_state(game) -> Dict:
    """Small, read-only extraction helper from game state for backdrop selection."""
    player = getattr(game, "player", None)
    if not player:
        return {}

    tm = getattr(game, "travel_manager", None)
    transport_mode = None
    if tm:
        if getattr(tm, "vehicle", None):
            vname = getattr(tm.vehicle, "name", "car").lower()
            if "limo" in vname:
                transport_mode = "limo"
            elif "bike" in vname:
                transport_mode = "bike"
            else:
                transport_mode = "car"
        else:
            transport_mode = getattr(tm, "transport_mode", None)

    lodging_tier = None
    poi = getattr(player, "current_poi", None)
    if poi:
        category = str(getattr(poi, "category", "")).upper()
        if "HOTEL" in category:
            lodging_tier = "luxury_house" if player.money >= 5000 else "apartment"
        elif "MOTEL" in category:
            lodging_tier = "rough_start"

    city = player.current_location.name if getattr(player, "current_location", None) else None
    vis = game.visibility_system.get_visibility(player.name, city) if hasattr(game, "visibility_system") else {}
    momentum = 0.0
    if hasattr(game, "reputation_system"):
        momentum = game.reputation_system.bias_for(player.name, location=city).get("momentum", 0.0)

    venue_tier = 0.0
    poi = getattr(player, "current_poi", None)
    if poi:
        venue_tier = float(getattr(poi, "prestige", 0.0) or 0.0)

    return {
        "money": getattr(player, "money", 0),
        "fame": getattr(player, "fame", 0),
        "has_home": getattr(player, "has_home", False),
        "transport_mode": transport_mode,
        "lodging_tier": lodging_tier,
        "public_visibility": float(vis.get("public_visibility", 0.0)),
        "recent_buzz": float(vis.get("recent_buzz", 0.0)),
        "momentum": float(momentum),
        "venue_tier": venue_tier,
        "home_key": f"{player.name}:{getattr(getattr(player, 'current_poi', None), 'poi_id', 'home')}",
        "transport_key": f"{player.name}:{transport_mode or 'ground'}",
        "work_key": f"{player.name}:{getattr(getattr(player, 'current_poi', None), 'poi_id', 'work')}",
        "public_key": f"{player.name}:{getattr(getattr(player, 'current_location', None), 'name', 'public')}",
    }


def style_shift(style_variant: str) -> int:
    try:
        return int(style_variant.replace("v", "")) - 2
    except Exception:
        return 0
