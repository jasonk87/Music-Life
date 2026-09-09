from typing import Dict, Any, Optional, List
import json
import os
import tempfile
import shutil
from game.state_archive import encode_game, decode_game
from types import SimpleNamespace

from game.game_time import current_game_time
from game.merch_system import MerchItem
from game.song import Song
from game.gear import GearItem
from game.superstardom import RecordPlaque
from game.label_imprint import IndieLabelImprint, SignedArtist
from game.vehicle_system import PlayerVehicle
from game.album_system import AlbumRelease, VinylBatchOrder
from game.music_video import MusicVideo
from game.streaming_dsp import TrackStreamingData, PlaylistPlacement
from game.real_estate import Property, HomeStudioGear
from game.tour_life_sim import BandmateContract
from game.major_label_system import MajorLabelContract
from game.billboard_charts import BillboardChartEntry
from game.sync_licensing import ActiveSyncPlacement, SyncOpportunity
from game.wellness_and_vices import MusicianHealthProfile
from game.finance_and_legal import BusinessManagerCPA, CopyrightLawsuit
from game.tour_logistics import SleeperTourBus, TouringCrewMember
from game.gear_maintenance import InstrumentMaintenanceStatus
from game.fan_club_and_pr import FanClubTier
from game.relationships_and_family import RomanticPartner, FamilyProfile
from game.pets_system import AdoptedPet
from game.hobbies_and_leisure import PersonalHobby
from game.fitness_and_outdoors import FitnessProfile
from game.investments_and_wealth import StockInvestment, CommercialProperty
from game.weather_and_seasons import CityWeatherReport
from game.rival_bands_and_trends import AIRivalBand, CulturalTrendEra
from game.stage_production import StageProductionRig
from game.music_press_reviews import AlbumReview
from game.press_podcasts import PublicPersonaProfile
from game.npc_system import NPC
from game.dynamic_musicians import AutonomousMusician, DynamicTrack
from game.international_touring import InternationalVisa
from game.physical_vinyl_drops import DirectVinylDrop, RecordStoreConsignment
from game.band_creative_tension import CreativeDisputeEvent


class JSONSaveManager:
    VERSION = "2.0"

    @staticmethod
    def serialize_game_time(gt) -> Dict[str, int]:
        return {
            "year": getattr(gt, "year", 2024),
            "month": getattr(gt, "month", 1),
            "day": getattr(gt, "day", 1),
            "hour": getattr(gt, "hour", 8),
            "minute": getattr(gt, "minute", 0),
        }

    @staticmethod
    def serialize_song(s) -> Dict[str, Any]:
        return {
            "song_id": getattr(s, "song_id", ""),
            "title": getattr(s, "title", "Untitled"),
            "artist": getattr(s, "author", getattr(s, "artist", "Unknown")),
            "theme": getattr(s, "theme", None),
            "release_date": JSONSaveManager.serialize_game_time(s.release_date) if getattr(s, "release_date", None) else None,
            "genre": getattr(s, "genre", "Indie"),
            "song_quality": getattr(s, "song_quality", 0.5),
            "recording_quality": getattr(s, "recording_quality", 0.5),
            "is_recorded": getattr(s, "is_recorded", False),
            "is_released": getattr(s, "is_released", False),
            "buzz_score": getattr(s, "buzz_score", 0),
            "released_by_label_id": getattr(s, "released_by_label_id", None),
            "sales_units": getattr(s, "sales_units", 0),
            "has_music_video": getattr(s, "has_music_video", False),
            "music_video_quality": getattr(s, "music_video_quality", 0.0),
        }

    @staticmethod
    def serialize_merch(m) -> Dict[str, Any]:
        return {
            "item_id": getattr(m, "item_id", ""),
            "name": getattr(m, "name", "Merch"),
            "category": getattr(m, "category", "general"),
            "cost_to_produce": getattr(m, "cost_to_produce", 10),
            "suggested_price": getattr(m, "suggested_price", 15),
            "current_price": getattr(m, "current_price", 15),
            "unit_count": getattr(m, "unit_count", getattr(m, "stock", 10)),
            "stock": getattr(m, "stock", 0),
            "total_sold": getattr(m, "total_sold", 0),
            "total_revenue": getattr(m, "total_revenue", 0),
            "quality": getattr(m, "quality", 1.0),
        }

    @staticmethod
    def serialize_gear(g) -> Dict[str, Any]:
        return {
            "item_id": getattr(g, "item_id", ""),
            "name": getattr(g, "name", "Item"),
            "description": getattr(g, "description", ""),
            "gear_type": getattr(g, "gear_type", "ACCESSORY"),
            "size": getattr(g, "size", 1),
            "cost": getattr(g, "cost", 0),
            "base_sell_price": getattr(g, "base_sell_price", 0),
            "hunger_reduction": getattr(g, "hunger_reduction", 0),
            "energy_boost": getattr(g, "energy_boost", 0),
            "durability": getattr(g, "durability", 100),
            "is_broken": getattr(g, "is_broken", False),
            "properties": getattr(g, "properties", {}),
        }

    @staticmethod
    def serialize_plaque(p) -> Dict[str, Any]:
        return {
            "title": getattr(p, "title", ""),
            "artist": getattr(p, "artist", ""),
            "cert_type": getattr(p, "cert_type", "Gold"),
            "sales_units": getattr(p, "sales_units", 0),
            "date_awarded": getattr(p, "date_awarded", ""),
        }

    @staticmethod
    def serialize_label_imprint(imp) -> Optional[Dict[str, Any]]:
        if not imp:
            return None
        roster_data = {}
        for nid, artist in imp.roster.items():
            roster_data[nid] = {
                "npc_id": artist.npc_id,
                "name": artist.name,
                "genre": artist.genre,
                "skill_level": artist.skill_level,
                "royalty_split": artist.royalty_split,
                "advance_paid": artist.advance_paid,
                "releases_count": artist.releases_count,
                "total_earnings_generated": artist.total_earnings_generated,
            }
        return {
            "label_name": imp.label_name,
            "owner_name": imp.owner_name,
            "total_label_revenue": imp.total_label_revenue,
            "roster": roster_data,
        }

    @staticmethod
    def serialize_vehicle(v) -> Optional[Dict[str, Any]]:
        if not v:
            return None
        return {
            "model_key": getattr(v, "model_key", "sedan_beatup"),
            "name": getattr(v, "name", "Vehicle"),
            "cost": getattr(v, "cost", 0),
            "speed": getattr(v, "speed", 65.0),
            "fuel_capacity": getattr(v, "fuel_capacity", 45.0),
            "fuel_current": getattr(v, "fuel_current", 45.0),
            "km_per_liter": getattr(v, "km_per_liter", 12.0),
            "reliability": getattr(v, "reliability", 0.65),
            "engine_condition": getattr(v, "engine_condition", 100.0),
        }

    @staticmethod
    def serialize_album(a) -> Dict[str, Any]:
        return {
            "album_id": a.album_id,
            "title": a.title,
            "artist": a.artist,
            "track_ids": a.track_ids,
            "tracks_data": a.tracks_data,
            "format_type": a.format_type,
            "release_date_str": a.release_date_str,
            "release_day": a.release_day,
            "genre": a.genre,
            "theme": a.theme,
            "overall_quality": a.overall_quality,
            "concept_coherence": a.concept_coherence,
            "total_physical_sales": a.total_physical_sales,
            "total_digital_sales": a.total_digital_sales,
            "total_revenue": a.total_revenue,
        }

    @staticmethod
    def serialize_vinyl_order(vo) -> Dict[str, Any]:
        return {
            "order_id": vo.order_id,
            "album_title": vo.album_title,
            "units_ordered": vo.units_ordered,
            "cost_per_unit": vo.cost_per_unit,
            "total_cost": vo.total_cost,
            "order_day": vo.order_day,
            "days_to_deliver": vo.days_to_deliver,
            "delivered": vo.delivered,
            "units_in_stock": vo.units_in_stock,
            "units_sold": vo.units_sold,
            "retail_price": vo.retail_price,
            "wholesale_price": vo.wholesale_price,
        }

    @staticmethod
    def serialize_music_video(mv) -> Dict[str, Any]:
        return {
            "video_id": mv.video_id,
            "song_id": mv.song_id,
            "song_title": mv.song_title,
            "tier": mv.tier,
            "production_cost": mv.production_cost,
            "director_name": mv.director_name,
            "concept": mv.concept,
            "views": mv.views,
            "likes": mv.likes,
            "viral_spike_active": mv.viral_spike_active,
            "release_day": mv.release_day,
        }

    @staticmethod
    def serialize_streaming_track(st) -> Dict[str, Any]:
        return {
            "song_id": st.song_id,
            "title": st.title,
            "genre": st.genre,
            "total_streams": st.total_streams,
            "daily_streams": st.daily_streams,
            "total_royalties_earned": st.total_royalties_earned,
            "release_day": st.release_day,
            "active_playlists": [
                {
                    "playlist_id": pl.playlist_id,
                    "name": pl.name,
                    "curator_type": pl.curator_type,
                    "genre": pl.genre,
                    "reach_followers": pl.reach_followers,
                    "daily_streams_boost": pl.daily_streams_boost,
                    "days_remaining": pl.days_remaining,
                }
                for pl in st.active_playlists
            ],
        }

    @staticmethod
    def serialize_real_estate(re) -> Dict[str, Any]:
        props_data = {}
        for pid, prop in re.properties.items():
            props_data[pid] = {
                "property_id": prop.property_id,
                "name": prop.name,
                "city": prop.city,
                "property_type": prop.property_type,
                "purchase_price": prop.purchase_price,
                "monthly_rent": prop.monthly_rent,
                "comfort_rating": prop.comfort_rating,
                "noise_tolerance": prop.noise_tolerance,
                "is_owned": prop.is_owned,
                "is_rented": prop.is_rented,
                "home_studio_installed": prop.home_studio_installed,
                "studio_gear": [
                    {
                        "gear_id": g.gear_id,
                        "name": g.name,
                        "category": g.category,
                        "cost": g.cost,
                        "quality_boost": g.quality_boost,
                        "desc": g.desc,
                    }
                    for g in prop.studio_gear
                ],
            }
        return {
            "current_residence_id": re.current_residence_id,
            "properties": props_data,
        }

    @staticmethod
    def serialize_bandmate_contract(bc) -> Dict[str, Any]:
        return {
            "member_name": bc.member_name,
            "role": bc.role,
            "publishing_split_pct": bc.publishing_split_pct,
            "weekly_wage": bc.weekly_wage,
            "burnout": bc.burnout,
            "satisfaction": bc.satisfaction,
            "ego": bc.ego,
        }

    @staticmethod
    def serialize_major_label_contract(c) -> Optional[Dict[str, Any]]:
        if not c:
            return None
        return {
            "contract_id": c.contract_id,
            "label_name": c.label_name,
            "city": c.city,
            "headquarters": c.headquarters,
            "advance_amount": c.advance_amount,
            "artist_royalty_pct": c.artist_royalty_pct,
            "recoupable_balance": c.recoupable_balance,
            "master_ownership_years": c.master_ownership_years,
            "has_360_deal": c.has_360_deal,
            "touring_cut_pct": c.touring_cut_pct,
            "merch_cut_pct": c.merch_cut_pct,
            "video_fund": c.video_fund,
            "albums_committed": c.albums_committed,
            "albums_delivered": c.albums_delivered,
            "is_active": c.is_active,
            "is_recouped": c.is_recouped,
            "is_shelved": c.is_shelved,
        }

    @staticmethod
    def serialize_billboard_entry(e) -> Dict[str, Any]:
        return {
            "song_id": e.song_id,
            "title": e.title,
            "artist": e.artist,
            "current_position": e.current_position,
            "peak_position": e.peak_position,
            "weeks_on_chart": e.weeks_on_chart,
            "points": e.points,
            "is_number_one": e.is_number_one,
        }

    @staticmethod
    def serialize_player(p) -> Dict[str, Any]:
        delegation = {}
        if hasattr(p, "delegation_roles"):
            for k, role in p.delegation_roles.items():
                delegation[k] = {
                    "role_type": getattr(role, "role_type", k),
                    "active": getattr(role, "active", True),
                    "upkeep": getattr(role, "upkeep", 100),
                    "competence": getattr(role, "competence", 0.5),
                    "reliability": getattr(role, "reliability", 0.5),
                    "experience": getattr(role, "experience", 0.5),
                }

        songs = [JSONSaveManager.serialize_song(s) for s in getattr(p, "songs_written", [])]
        merch = [JSONSaveManager.serialize_merch(m) for m in getattr(p, "merch_stock", [])]
        gear = [JSONSaveManager.serialize_gear(g) for g in getattr(p, "gear_inventory", [])]
        home_gear = [JSONSaveManager.serialize_gear(g) for g in getattr(p, "home_storage", [])]
        veh_data = JSONSaveManager.serialize_vehicle(getattr(p, "vehicle", None))

        return {
            "name": getattr(p, "name", "Musician"),
            "money": getattr(p, "money", 500),
            "fame": getattr(p, "fame", 0),
            "street_cred": getattr(p, "street_cred", 50),
            "energy": getattr(p, "energy", 100),
            "stress": getattr(p, "stress", 0),
            "hunger": getattr(p, "hunger", 0),
            "health": getattr(p, "health", 100),
            "comfort": getattr(p, "comfort", 70),
            "skills": getattr(p, "skills", {}),
            "has_home": getattr(p, "has_home", True),
            "current_location_name": p.current_location.name if hasattr(p.current_location, "name") else (p.current_location if isinstance(getattr(p, "current_location", None), str) else "Asbury Park, NJ"),
            "current_poi_id": getattr(p.current_poi, "poi_id", None) if getattr(p, "current_poi", None) else None,
            "songs_written": songs,
            "merch_stock": merch,
            "gear_inventory": gear,
            "home_storage": home_gear,
            "vehicle": veh_data,
            "delegation_roles": delegation,
            "contacts": getattr(p, "contacts", []),
            "signed_label_deal": getattr(p, "signed_label_deal", None),
        }

    @classmethod
    def save_game(cls, game, filepath="savegame.json") -> bool:
        try:
            superstardom_data = {
                "plaques": [cls.serialize_plaque(pl) for pl in getattr(game.superstardom, "plaques", [])] if hasattr(game, "superstardom") else [],
                "awards_won": getattr(game.superstardom, "awards_won", []) if hasattr(game, "superstardom") else [],
            }
            label_data = cls.serialize_label_imprint(getattr(game, "label_imprint", None))

            album_data = {
                "released_albums": [cls.serialize_album(a) for a in getattr(game.album_system, "released_albums", [])] if hasattr(game, "album_system") else [],
                "pending_vinyl_orders": [cls.serialize_vinyl_order(vo) for vo in getattr(game.album_system, "pending_vinyl_orders", [])] if hasattr(game, "album_system") else [],
                "delivered_vinyl_batches": [cls.serialize_vinyl_order(vo) for vo in getattr(game.album_system, "delivered_vinyl_batches", [])] if hasattr(game, "album_system") else [],
            }

            video_data = [cls.serialize_music_video(v) for v in getattr(game.music_video_system, "videos", [])] if hasattr(game, "music_video_system") else []

            streaming_data = {
                "catalog": {sid: cls.serialize_streaming_track(st) for sid, st in getattr(game.streaming_system, "catalog", {}).items()} if hasattr(game, "streaming_system") else {},
                "accumulated_unpaid_royalties": getattr(game.streaming_system, "accumulated_unpaid_royalties", 0.0) if hasattr(game, "streaming_system") else 0.0,
            }

            real_estate_data = cls.serialize_real_estate(game.real_estate_system) if hasattr(game, "real_estate_system") else {}

            tour_data = {
                "contracts": {name: cls.serialize_bandmate_contract(c) for name, c in getattr(game.tour_life_simulation, "contracts", {}).items()} if hasattr(game, "tour_life_simulation") else {},
            }

            major_label_data = cls.serialize_major_label_contract(game.major_label_system.signed_contract) if hasattr(game, "major_label_system") else None

            media_fest_data = {
                "tv_performances": getattr(game.media_and_festivals_system, "tv_performances_logged", []) if hasattr(game, "media_and_festivals_system") else [],
                "festival_sets": getattr(game.media_and_festivals_system, "festival_sets_logged", []) if hasattr(game, "media_and_festivals_system") else [],
            }

            vintage_data = [g.gear_id for g in getattr(game.vintage_gear_network, "owned_grails", [])] if hasattr(game, "vintage_gear_network") else []

            billboard_data = {
                "chart_entries": {sid: cls.serialize_billboard_entry(e) for sid, e in getattr(game.billboard_charts, "chart_entries", {}).items()} if hasattr(game, "billboard_charts") else {},
                "number_one_milestones": getattr(game.billboard_charts, "number_one_milestones", []) if hasattr(game, "billboard_charts") else [],
            }

            sync_data = {
                "active_placements": [
                    {
                        "placement_id": pl.placement_id,
                        "song_id": pl.song_id,
                        "song_title": pl.song_title,
                        "opportunity_id": pl.opportunity.opportunity_id,
                        "day_placed": pl.day_placed,
                        "days_remaining": pl.days_remaining,
                        "total_fee_earned": pl.total_fee_earned,
                    }
                    for pl in getattr(game.sync_licensing_system, "active_placements", [])
                ] if hasattr(game, "sync_licensing_system") else [],
                "completed_placements_count": getattr(game.sync_licensing_system, "completed_placements_count", 0) if hasattr(game, "sync_licensing_system") else 0,
            }

            wellness_data = {
                "addiction_meter": game.wellness_and_vices_system.profile.addiction_meter,
                "vocal_fatigue": game.wellness_and_vices_system.profile.vocal_fatigue,
                "sobriety_streak_days": game.wellness_and_vices_system.profile.sobriety_streak_days,
                "is_in_rehab": game.wellness_and_vices_system.profile.is_in_rehab,
                "vocal_coaching_level": game.wellness_and_vices_system.profile.vocal_coaching_level,
                "lifelong_stamina_bonus": game.wellness_and_vices_system.profile.lifelong_stamina_bonus,
            } if hasattr(game, "wellness_and_vices_system") else {}

            finance_data = {
                "hired_cpa": {
                    "name": game.finance_and_legal_system.hired_cpa.name,
                    "city": game.finance_and_legal_system.hired_cpa.city,
                    "agency_firm": game.finance_and_legal_system.hired_cpa.agency_firm,
                    "annual_retainer": game.finance_and_legal_system.hired_cpa.annual_retainer,
                    "tax_deduction_efficiency": game.finance_and_legal_system.hired_cpa.tax_deduction_efficiency,
                } if hasattr(game, "finance_and_legal_system") and game.finance_and_legal_system.hired_cpa else None,
                "total_taxes_paid": getattr(game.finance_and_legal_system, "total_taxes_paid", 0) if hasattr(game, "finance_and_legal_system") else 0,
                "last_tax_year": getattr(game.finance_and_legal_system, "last_tax_year", 2023) if hasattr(game, "finance_and_legal_system") else 2023,
            }

            logistics_data = {
                "tour_bus": {
                    "bus_id": game.tour_logistics_system.tour_bus.bus_id,
                    "model_name": game.tour_logistics_system.tour_bus.model_name,
                    "is_leased": game.tour_logistics_system.tour_bus.is_leased,
                    "is_owned": game.tour_logistics_system.tour_bus.is_owned,
                    "comfort_rating": game.tour_logistics_system.tour_bus.comfort_rating,
                } if hasattr(game, "tour_logistics_system") and game.tour_logistics_system.tour_bus else None,
                "hired_crew": {
                    k: {
                        "crew_id": c.crew_id,
                        "role_type": c.role_type,
                        "name": c.name,
                        "weekly_salary": c.weekly_salary,
                        "audio_boost": c.audio_boost,
                        "hype_boost": c.hype_boost,
                        "zero_gear_mishaps": c.zero_gear_mishaps,
                        "route_efficiency": c.route_efficiency,
                    }
                    for k, c in getattr(game.tour_logistics_system, "hired_crew", {}).items()
                } if hasattr(game, "tour_logistics_system") else {},
            }

            gear_maint_data = {
                "condition_pct": game.gear_maintenance_system.maintenance_status.condition_pct,
                "fret_wear_pct": game.gear_maintenance_system.maintenance_status.fret_wear_pct,
                "tube_amp_bias_ok": game.gear_maintenance_system.maintenance_status.tube_amp_bias_ok,
                "has_overnight_security": getattr(game.gear_maintenance_system, "has_overnight_security", False),
            } if hasattr(game, "gear_maintenance_system") else {}

            fan_club_data = {
                "is_club_launched": game.fan_club_and_pr_system.is_club_launched,
                "accumulated_club_revenue": game.fan_club_and_pr_system.accumulated_club_revenue,
                "tiers": {
                    k: {
                        "tier_name": t.tier_name,
                        "price_per_month": t.price_per_month,
                        "subscribers_count": t.subscribers_count,
                        "perks_desc": t.perks_desc,
                    }
                    for k, t in getattr(game.fan_club_and_pr_system, "tiers", {}).items()
                },
            } if hasattr(game, "fan_club_and_pr_system") else {}

            relationships_data = {
                "partner": {
                    "partner_id": game.relationships_and_family.partner.partner_id,
                    "name": game.relationships_and_family.partner.name,
                    "city": game.relationships_and_family.partner.city,
                    "occupation": game.relationships_and_family.partner.occupation,
                    "personality_trait": game.relationships_and_family.partner.personality_trait,
                    "affection_level": game.relationships_and_family.partner.affection_level,
                    "relationship_status": game.relationships_and_family.partner.relationship_status,
                    "shared_home": game.relationships_and_family.partner.shared_home,
                } if hasattr(game, "relationships_and_family") and game.relationships_and_family.partner else None,
                "family": {
                    "parents_relationship": game.relationships_and_family.family.parents_relationship,
                    "total_money_sent_home": game.relationships_and_family.family.total_money_sent_home,
                    "homesickness_meter": game.relationships_and_family.family.homesickness_meter,
                } if hasattr(game, "relationships_and_family") else {},
            }

            pets_data = [
                {
                    "pet_id": p.pet_id,
                    "name": p.name,
                    "species": p.species,
                    "breed": p.breed,
                    "city_adopted": p.city_adopted,
                    "happiness": p.happiness,
                    "hunger": p.hunger,
                    "is_tour_companion": p.is_tour_companion,
                    "personality": p.personality,
                }
                for p in getattr(game.pets_system, "pets", [])
            ] if hasattr(game, "pets_system") else []

            hobbies_data = {
                k: {
                    "hobby_key": h.hobby_key,
                    "name": h.name,
                    "skill_level": h.skill_level,
                    "gear_owned": h.gear_owned,
                    "total_hours_spent": h.total_hours_spent,
                    "description": h.description,
                }
                for k, h in getattr(game.hobbies_and_leisure, "hobbies", {}).items()
            } if hasattr(game, "hobbies_and_leisure") else {}

            fitness_data = {
                "physical_conditioning_level": game.fitness_and_outdoors.profile.physical_conditioning_level,
                "stamina_bonus_earned": game.fitness_and_outdoors.profile.stamina_bonus_earned,
                "gym_membership_active": game.fitness_and_outdoors.profile.gym_membership_active,
                "workouts_completed": game.fitness_and_outdoors.profile.workouts_completed,
                "martial_arts_belt": game.fitness_and_outdoors.profile.martial_arts_belt,
            } if hasattr(game, "fitness_and_outdoors") else {}

            investments_data = {
                "stocks": {
                    sym: {
                        "symbol": s.symbol,
                        "name": s.name,
                        "shares_owned": s.shares_owned,
                        "total_invested": s.total_invested,
                        "current_value": s.current_value,
                        "dividend_yield_pct": s.dividend_yield_pct,
                    }
                    for sym, s in getattr(game.investments_and_wealth, "stocks", {}).items()
                } if hasattr(game, "investments_and_wealth") else {},
                "commercial_properties": {
                    k: {
                        "property_key": cp.property_key,
                        "name": cp.name,
                        "city": cp.city,
                        "purchase_price": cp.purchase_price,
                        "monthly_rental_income": cp.monthly_rental_income,
                        "is_owned": cp.is_owned,
                    }
                    for k, cp in getattr(game.investments_and_wealth, "commercial_properties", {}).items()
                } if hasattr(game, "investments_and_wealth") else {},
                "total_dividends_earned": getattr(game.investments_and_wealth, "total_dividends_earned", 0.0) if hasattr(game, "investments_and_wealth") else 0.0,
                "total_commercial_rent_earned": getattr(game.investments_and_wealth, "total_commercial_rent_earned", 0) if hasattr(game, "investments_and_wealth") else 0,
            }

            charity_data = {
                "completed_donations": getattr(game.community_charity, "completed_donations", []) if hasattr(game, "community_charity") else [],
                "total_donated": getattr(game.community_charity, "total_donated", 0) if hasattr(game, "community_charity") else 0,
            }

            rivals_data = {
                "rivals": {
                    k: {
                        "band_id": r.band_id,
                        "name": r.name,
                        "home_city": r.home_city,
                        "genre": r.genre,
                        "fame": r.fame,
                        "buzz_score": r.buzz_score,
                        "latest_hit": r.latest_hit,
                    }
                    for k, r in getattr(game.rival_bands_and_trends, "rivals", {}).items()
                } if hasattr(game, "rival_bands_and_trends") else {},
                "active_trend": {
                    "trend_id": game.rival_bands_and_trends.active_trend.trend_id,
                    "name": game.rival_bands_and_trends.active_trend.name,
                    "dominant_genre": game.rival_bands_and_trends.active_trend.dominant_genre,
                    "multiplier": game.rival_bands_and_trends.active_trend.multiplier,
                    "days_remaining": game.rival_bands_and_trends.active_trend.days_remaining,
                    "description": game.rival_bands_and_trends.active_trend.description,
                } if hasattr(game, "rival_bands_and_trends") else {},
            }

            stage_data = {
                "active_rig_id": game.stage_production.active_rig.rig_id,
                "owned_rig_ids": game.stage_production.owned_rig_ids,
            } if hasattr(game, "stage_production") else {}

            reviews_data = [
                {
                    "review_id": rev.review_id,
                    "album_id": rev.album_id,
                    "album_title": rev.album_title,
                    "publication": rev.publication,
                    "numeric_score": rev.numeric_score,
                    "is_best_new_music": rev.is_best_new_music,
                    "review_headline": rev.review_headline,
                    "review_blurb": rev.review_blurb,
                    "day_published": rev.day_published,
                }
                for rev in getattr(game.music_press_reviews, "review_archive", [])
            ] if hasattr(game, "music_press_reviews") else []

            persona_data = {
                "auteur_score": game.press_podcasts.persona.auteur_score,
                "working_class_score": game.press_podcasts.persona.working_class_score,
                "maverick_score": game.press_podcasts.persona.maverick_score,
                "total_podcasts_done": game.press_podcasts.persona.total_podcasts_done,
                "podcast_history": getattr(game.press_podcasts, "podcast_history", []),
            } if hasattr(game, "press_podcasts") else {}

            npc_data = {
                k: {
                    "npc_id": n.npc_id,
                    "name": n.name,
                    "city": n.city,
                    "poi_id": n.poi_id,
                    "role": n.role,
                    "affinity": n.affinity,
                    "respect": n.respect,
                    "favors_available": n.favors_available,
                    "favors_used": n.favors_used,
                    "memories": n.memories,
                }
                for k, n in getattr(game.npc_system, "npcs", {}).items()
            } if hasattr(game, "npc_system") else {}

            dynamic_musicians_data = {
                k: {
                    "artist_id": m.artist_id,
                    "name": m.name,
                    "band_type": m.band_type,
                    "genre": m.genre,
                    "skill_level": m.skill_level,
                    "fame": m.fame,
                    "funds": m.funds,
                    "current_city": m.current_city,
                    "destination_city": m.destination_city,
                    "travel_days_left": m.travel_days_left,
                    "status": m.status,
                    "energy": m.energy,
                    "stress": m.stress,
                    "current_poi_id": m.current_poi_id,
                    "tour_itinerary": m.tour_itinerary,
                    "affinity_with_player": m.affinity_with_player,
                    "co_headlining_with_player": m.co_headlining_with_player,
                    "is_signed_to_player_label": m.is_signed_to_player_label,
                    "catalog": [
                        {
                            "title": t.title,
                            "genre": t.genre,
                            "quality": t.quality,
                            "streams": t.streams,
                        }
                        for t in m.catalog
                    ],
                }
                for k, m in getattr(game.dynamic_musicians, "musicians", {}).items()
            } if hasattr(game, "dynamic_musicians") else {}

            # v1.9 International Touring & Customs
            international_tour_data = {
                "active_visas": {
                    vid: {
                        "visa_id": v.visa_id,
                        "territory": v.territory,
                        "cost": v.cost,
                        "days_valid": v.days_valid,
                        "is_active": v.is_active,
                        "approved_day": v.approved_day,
                    }
                    for vid, v in getattr(game.international_touring, "active_visas", {}).items()
                } if hasattr(game, "international_touring") else {},
                "has_ata_carnet_bond": getattr(game.international_touring, "has_ata_carnet_bond", False) if hasattr(game, "international_touring") else False,
                "jet_lag_fatigue": getattr(game.international_touring, "jet_lag_fatigue", 0) if hasattr(game, "international_touring") else 0,
            }

            # v1.9 Physical Vinyl Drops & Consignment
            physical_drops_data = {
                "active_webstore_drops": [
                    {
                        "drop_id": d.drop_id,
                        "album_title": d.album_title,
                        "variant_name": d.variant_name,
                        "units_total": d.units_total,
                        "units_remaining": d.units_remaining,
                        "unit_price": d.unit_price,
                        "total_revenue_earned": d.total_revenue_earned,
                        "is_sold_out": d.is_sold_out,
                    }
                    for d in getattr(game.physical_vinyl_drops, "active_webstore_drops", [])
                ] if hasattr(game, "physical_vinyl_drops") else [],
                "consignments": [
                    {
                        "store_name": c.store_name,
                        "city_name": c.city_name,
                        "album_title": c.album_title,
                        "units_consigned": c.units_consigned,
                        "units_sold": c.units_sold,
                        "wholesale_rate": c.wholesale_rate,
                        "total_payout": c.total_payout,
                    }
                    for c in getattr(game.physical_vinyl_drops, "consignments", [])
                ] if hasattr(game, "physical_vinyl_drops") else [],
                "total_vinyl_drop_revenue": getattr(game.physical_vinyl_drops, "total_vinyl_drop_revenue", 0) if hasattr(game, "physical_vinyl_drops") else 0,
            }

            # v1.9 Band Creative Tension
            band_tension_data = {
                "dispute_history": [
                    {
                        "event_id": ev.event_id,
                        "title": ev.title,
                        "member_name": ev.member_name,
                        "song_title": ev.song_title,
                        "description": ev.description,
                        "options": ev.options,
                        "resolved": ev.resolved,
                        "chosen_option_index": ev.chosen_option_index,
                    }
                    for ev in getattr(game.band_creative_tension, "dispute_history", [])
                ] if hasattr(game, "band_creative_tension") else [],
            }

            payload = {
                "version": cls.VERSION,
                "career_archive": encode_game(game),
                "game_time": cls.serialize_game_time(current_game_time),
                "player": cls.serialize_player(game.player),
                "superstardom": superstardom_data,
                "label_imprint": label_data,
                "album_system": album_data,
                "music_videos": video_data,
                "streaming_platform": streaming_data,
                "real_estate": real_estate_data,
                "tour_life": tour_data,
                "major_label_deal": major_label_data,
                "media_and_festivals": media_fest_data,
                "vintage_gear": vintage_data,
                "billboard_charts": billboard_data,
                "sync_licensing": sync_data,
                "wellness_and_vices": wellness_data,
                "finance_and_legal": finance_data,
                "tour_logistics": logistics_data,
                "gear_maintenance": gear_maint_data,
                "fan_club": fan_club_data,
                "relationships_and_family": relationships_data,
                "pets": pets_data,
                "hobbies": hobbies_data,
                "fitness": fitness_data,
                "investments": investments_data,
                "charity": charity_data,
                "rivals_and_trends": rivals_data,
                "stage_production": stage_data,
                "music_reviews": reviews_data,
                "public_persona": persona_data,
                "npcs": npc_data,
                "dynamic_musicians": dynamic_musicians_data,
                "international_touring": international_tour_data,
                "physical_vinyl_drops": physical_drops_data,
                "band_creative_tension": band_tension_data,
            }
            # Serialize fully before touching an existing save. Atomic replacement
            # leaves either the previous complete save or the new complete save.
            content = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)
            destination = os.path.abspath(filepath)
            parent = os.path.dirname(destination)
            fd, temporary = tempfile.mkstemp(prefix=".music-life-", suffix=".tmp", dir=parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                if os.path.exists(destination):
                    shutil.copy2(destination, destination + ".bak")
                os.replace(temporary, destination)
            finally:
                if os.path.exists(temporary): os.remove(temporary)
            if hasattr(game, "GAME_LOG") and hasattr(game.GAME_LOG, "add_log_message"):
                game.GAME_LOG.add_log_message(f"Game saved to {filepath}.")
            return True
        except Exception as e:
            if hasattr(game, "GAME_LOG") and hasattr(game.GAME_LOG, "add_log_message"):
                game.GAME_LOG.add_log_message(f"Save error: {e}")
            return False

    @classmethod
    def load_game(cls, game, filepath="savegame.json") -> bool:
        if not os.path.exists(filepath):
            if hasattr(game, "GAME_LOG") and hasattr(game.GAME_LOG, "add_log_message"):
                game.GAME_LOG.add_log_message(f"No save file found at {filepath}.")
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                payload = json.load(f)

            if "career_archive" in payload:
                roots = decode_game(payload["career_archive"], game)
                clock = payload["game_time"]
                if not (1 <= clock["month"] <= 12 and 1 <= clock["day"] <= 30 and 0 <= clock["hour"] < 24 and 0 <= clock["minute"] < 60):
                    raise ValueError("Invalid saved clock")
                game.__dict__.update(roots)
                for key in ("year", "month", "day", "hour", "minute"):
                    setattr(current_game_time, key, clock[key])
                game._build_poi_venue_id_map()
                game.game_state = "main_menu"
                if hasattr(game.GAME_LOG, "add_log_message"):
                    game.GAME_LOG.add_log_message("Career restored. Calendar, world and relationships recovered.")
                return True

            gt_data = payload.get("game_time", {})
            if gt_data:
                current_game_time.year = gt_data.get("year", 2024)
                current_game_time.month = gt_data.get("month", 1)
                current_game_time.day = gt_data.get("day", 1)
                current_game_time.hour = gt_data.get("hour", 8)
                current_game_time.minute = gt_data.get("minute", 0)

            p_data = payload.get("player", {})
            if p_data:
                if getattr(game, "player", None) is None:
                    from game.player import Player
                    game.player = Player(p_data.get("name", "Musician"))
                p = game.player
                p.name = p_data.get("name", p.name)
                p.money = p_data.get("money", p.money)
                p.fame = p_data.get("fame", p.fame)
                p.street_cred = p_data.get("street_cred", p.street_cred)
                p.energy = p_data.get("energy", p.energy)
                p.stress = p_data.get("stress", p.stress)
                p.hunger = p_data.get("hunger", p.hunger)
                p.health = p_data.get("health", p.health)
                p.comfort = p_data.get("comfort", p.comfort)
                p.skills = p_data.get("skills", p.skills)
                p.has_home = p_data.get("has_home", p.has_home)
                p.contacts = p_data.get("contacts", [])

                loc_name = p_data.get("current_location_name")
                if loc_name and hasattr(game, "WORLD_MAP") and loc_name in game.WORLD_MAP:
                    p.current_location = game.WORLD_MAP[loc_name]
                elif loc_name:
                    p.current_location = SimpleNamespace(name=loc_name)

                poi_id = p_data.get("current_poi_id")
                if poi_id and hasattr(game, "get_poi_or_venue_by_id"):
                    poi = game.get_poi_or_venue_by_id(poi_id)
                    if poi:
                        p.current_poi = poi

                # Songs deserialization
                if "songs_written" in p_data:
                    p.songs_written.clear()
                    for s_info in p_data["songs_written"]:
                        song = Song(
                            title=s_info.get("title", "Untitled"),
                            author=s_info.get("artist", p.name),
                            genre=s_info.get("genre", "Indie"),
                            song_quality=s_info.get("song_quality", 0.5),
                            theme=s_info.get("theme"),
                        )
                        from game.game_time import GameTime
                        release = s_info.get("release_date")
                        if isinstance(release, dict):
                            song.release_date = GameTime(release["year"], release["month"], release["day"], release["hour"], release["minute"])
                        elif s_info.get("is_released"):
                            song.release_date = current_game_time.copy()
                        song.song_id = s_info.get("song_id", song.song_id)
                        song.recording_quality = s_info.get("recording_quality", 0.5)
                        song.is_recorded = s_info.get("is_recorded", False)
                        song.is_released = s_info.get("is_released", False)
                        song.buzz_score = s_info.get("buzz_score", 0)
                        song.released_by_label_id = s_info.get("released_by_label_id", None)
                        song.sales_units = s_info.get("sales_units", 0)
                        song.has_music_video = s_info.get("has_music_video", False)
                        song.music_video_quality = s_info.get("music_video_quality", 0.0)
                        p.songs_written.append(song)

                # Merch deserialization
                if "merch_stock" in p_data:
                    p.merch_stock.clear()
                    for m_info in p_data["merch_stock"]:
                        merch_item = MerchItem(
                            item_id=m_info.get("item_id", ""),
                            name=m_info.get("name", "Merch"),
                            category=m_info.get("category", "general"),
                            cost_to_produce=m_info.get("cost_to_produce", 10),
                            suggested_price=m_info.get("suggested_price", 15),
                            unit_count=m_info.get("unit_count", m_info.get("stock", 10)),
                            quality=m_info.get("quality", 1.0),
                        )
                        merch_item.current_price = m_info.get("current_price", 15)
                        merch_item.stock = m_info.get("stock", 0)
                        merch_item.total_sold = m_info.get("total_sold", 0)
                        merch_item.total_revenue = m_info.get("total_revenue", 0)
                        p.merch_stock.append(merch_item)

                # Gear inventory deserialization
                if "gear_inventory" in p_data:
                    p.gear_inventory.clear()
                    for g_info in p_data["gear_inventory"]:
                        gear_item = GearItem(
                            item_id=g_info.get("item_id", ""),
                            name=g_info.get("name", "Item"),
                            description=g_info.get("description", ""),
                            gear_type=g_info.get("gear_type", "ACCESSORY"),
                            size=g_info.get("size", 1),
                            cost=g_info.get("cost", 0),
                            base_sell_price=g_info.get("base_sell_price", 0),
                            hunger_reduction=g_info.get("hunger_reduction", 0),
                            energy_boost=g_info.get("energy_boost", 0),
                            properties=g_info.get("properties", {}),
                        )
                        gear_item.durability = g_info.get("durability", 100)
                        gear_item.is_broken = g_info.get("is_broken", False)
                        p.gear_inventory.append(gear_item)

                # Home storage deserialization
                if "home_storage" in p_data:
                    p.home_storage.clear()
                    for g_info in p_data["home_storage"]:
                        gear_item = GearItem(
                            item_id=g_info.get("item_id", ""),
                            name=g_info.get("name", "Item"),
                            description=g_info.get("description", ""),
                            gear_type=g_info.get("gear_type", "ACCESSORY"),
                            size=g_info.get("size", 1),
                            cost=g_info.get("cost", 0),
                            base_sell_price=g_info.get("base_sell_price", 0),
                            hunger_reduction=g_info.get("hunger_reduction", 0),
                            energy_boost=g_info.get("energy_boost", 0),
                            properties=g_info.get("properties", {}),
                        )
                        gear_item.durability = g_info.get("durability", 100)
                        gear_item.is_broken = g_info.get("is_broken", False)
                        p.home_storage.append(gear_item)

                # Vehicle deserialization
                if "vehicle" in p_data and p_data["vehicle"]:
                    v_data = p_data["vehicle"]
                    p.vehicle = PlayerVehicle(
                        model_key=v_data.get("model_key", "sedan_beatup"),
                        name=v_data.get("name", "Vehicle"),
                        cost=v_data.get("cost", 0),
                        speed=v_data.get("speed", 65.0),
                        fuel_capacity=v_data.get("fuel_capacity", 45.0),
                        km_per_liter=v_data.get("km_per_liter", 12.0),
                        reliability=v_data.get("reliability", 0.65),
                    )
                    p.vehicle.fuel_current = v_data.get("fuel_current", p.vehicle.fuel_capacity)
                    p.vehicle.engine_condition = v_data.get("engine_condition", 100.0)
                elif "vehicle" in p_data and p_data["vehicle"] is None:
                    p.vehicle = None

                # Delegation roles deserialization
                if "delegation_roles" in p_data and hasattr(game, "delegation_system"):
                    game.delegation_system.ensure_player_support(p)
                    for r_type, r_info in p_data["delegation_roles"].items():
                        game.delegation_system.add_or_update_role(
                            p,
                            r_type,
                            active=r_info.get("active", True),
                            competence=r_info.get("competence", 0.5),
                            reliability=r_info.get("reliability", 0.5),
                            upkeep=r_info.get("upkeep", 100),
                            experience=r_info.get("experience", 0.5),
                        )

                if "signed_label_deal" in p_data:
                    p.signed_label_deal = p_data["signed_label_deal"]

            # Superstardom deserialization
            if "superstardom" in payload and hasattr(game, "superstardom"):
                game.superstardom.plaques.clear()
                game.superstardom.awards_won.clear()
                for pl_info in payload["superstardom"].get("plaques", []):
                    plaque = RecordPlaque(
                        title=pl_info.get("title", ""),
                        artist=pl_info.get("artist", p.name),
                        cert_type=pl_info.get("cert_type", "Gold"),
                        sales_units=pl_info.get("sales_units", 0),
                        date_awarded=pl_info.get("date_awarded", ""),
                    )
                    game.superstardom.plaques.append(plaque)
                game.superstardom.awards_won.extend(payload["superstardom"].get("awards_won", []))

            # Label imprint deserialization
            if "label_imprint" in payload and payload["label_imprint"]:
                limp = payload["label_imprint"]
                imprint = IndieLabelImprint(limp.get("label_name", "My Label"), limp.get("owner_name", p.name))
                imprint.total_label_revenue = limp.get("total_label_revenue", 0.0)
                for nid, a_info in limp.get("roster", {}).items():
                    artist = SignedArtist(
                        npc_id=a_info.get("npc_id", nid),
                        name=a_info.get("name", "Artist"),
                        genre=a_info.get("genre", "Indie"),
                        skill_level=a_info.get("skill_level", 5),
                        royalty_split=a_info.get("royalty_split", 0.5),
                        advance_paid=a_info.get("advance_paid", 500),
                        releases_count=a_info.get("releases_count", 0),
                        total_earnings_generated=a_info.get("total_earnings_generated", 0.0),
                    )
                    imprint.roster[nid] = artist
                game.label_imprint = imprint

            # Album system deserialization
            if "album_system" in payload and hasattr(game, "album_system"):
                as_data = payload["album_system"]
                game.album_system.released_albums.clear()
                for a_info in as_data.get("released_albums", []):
                    album = AlbumRelease(
                        album_id=a_info.get("album_id", ""),
                        title=a_info.get("title", "Album"),
                        artist=a_info.get("artist", "Artist"),
                        track_ids=a_info.get("track_ids", []),
                        tracks_data=a_info.get("tracks_data", []),
                        format_type=a_info.get("format_type", "DIGITAL"),
                        release_date_str=a_info.get("release_date_str", ""),
                        release_day=a_info.get("release_day", 1),
                        genre=a_info.get("genre", "Indie"),
                        theme=a_info.get("theme", None),
                        overall_quality=a_info.get("overall_quality", 0.5),
                        concept_coherence=a_info.get("concept_coherence", 1.0),
                        total_physical_sales=a_info.get("total_physical_sales", 0),
                        total_digital_sales=a_info.get("total_digital_sales", 0),
                        total_revenue=a_info.get("total_revenue", 0.0),
                    )
                    game.album_system.released_albums.append(album)

                game.album_system.pending_vinyl_orders.clear()
                for vo_info in as_data.get("pending_vinyl_orders", []):
                    order = VinylBatchOrder(
                        order_id=vo_info.get("order_id", ""),
                        album_title=vo_info.get("album_title", ""),
                        units_ordered=vo_info.get("units_ordered", 500),
                        cost_per_unit=vo_info.get("cost_per_unit", 6.0),
                        total_cost=vo_info.get("total_cost", 3000.0),
                        order_day=vo_info.get("order_day", 1),
                        days_to_deliver=vo_info.get("days_to_deliver", 21),
                        delivered=vo_info.get("delivered", False),
                        units_in_stock=vo_info.get("units_in_stock", 0),
                        units_sold=vo_info.get("units_sold", 0),
                        retail_price=vo_info.get("retail_price", 25.0),
                        wholesale_price=vo_info.get("wholesale_price", 15.0),
                    )
                    game.album_system.pending_vinyl_orders.append(order)

                game.album_system.delivered_vinyl_batches.clear()
                for vo_info in as_data.get("delivered_vinyl_batches", []):
                    order = VinylBatchOrder(
                        order_id=vo_info.get("order_id", ""),
                        album_title=vo_info.get("album_title", ""),
                        units_ordered=vo_info.get("units_ordered", 500),
                        cost_per_unit=vo_info.get("cost_per_unit", 6.0),
                        total_cost=vo_info.get("total_cost", 3000.0),
                        order_day=vo_info.get("order_day", 1),
                        days_to_deliver=vo_info.get("days_to_deliver", 21),
                        delivered=vo_info.get("delivered", True),
                        units_in_stock=vo_info.get("units_in_stock", 500),
                        units_sold=vo_info.get("units_sold", 0),
                        retail_price=vo_info.get("retail_price", 25.0),
                        wholesale_price=vo_info.get("wholesale_price", 15.0),
                    )
                    game.album_system.delivered_vinyl_batches.append(order)

            # Music videos deserialization
            if "music_videos" in payload and hasattr(game, "music_video_system"):
                game.music_video_system.videos.clear()
                for v_info in payload.get("music_videos", []):
                    mv = MusicVideo(
                        video_id=v_info.get("video_id", ""),
                        song_id=v_info.get("song_id", ""),
                        song_title=v_info.get("song_title", "Track"),
                        tier=v_info.get("tier", "DIY"),
                        production_cost=v_info.get("production_cost", 150),
                        director_name=v_info.get("director_name", "Self-Directed"),
                        concept=v_info.get("concept", "Performance"),
                        views=v_info.get("views", 0),
                        likes=v_info.get("likes", 0),
                        viral_spike_active=v_info.get("viral_spike_active", False),
                        release_day=v_info.get("release_day", 1),
                    )
                    game.music_video_system.videos.append(mv)

            # Streaming platform deserialization
            if "streaming_platform" in payload and hasattr(game, "streaming_system"):
                sp_data = payload["streaming_platform"]
                game.streaming_system.accumulated_unpaid_royalties = sp_data.get("accumulated_unpaid_royalties", 0.0)
                game.streaming_system.catalog.clear()
                for sid, t_info in sp_data.get("catalog", {}).items():
                    track = TrackStreamingData(
                        song_id=t_info.get("song_id", sid),
                        title=t_info.get("title", "Track"),
                        genre=t_info.get("genre", "Indie"),
                        total_streams=t_info.get("total_streams", 0),
                        daily_streams=t_info.get("daily_streams", 0),
                        total_royalties_earned=t_info.get("total_royalties_earned", 0.0),
                        release_day=t_info.get("release_day", 1),
                    )
                    for pl_info in t_info.get("active_playlists", []):
                        pl = PlaylistPlacement(
                            playlist_id=pl_info.get("playlist_id", ""),
                            name=pl_info.get("name", "Playlist"),
                            curator_type=pl_info.get("curator_type", "EDITORIAL"),
                            genre=pl_info.get("genre", "Indie"),
                            reach_followers=pl_info.get("reach_followers", 10000),
                            daily_streams_boost=pl_info.get("daily_streams_boost", 500),
                            days_remaining=pl_info.get("days_remaining", 14),
                        )
                        track.active_playlists.append(pl)
                    game.streaming_system.catalog[sid] = track

            # Real estate deserialization
            if "real_estate" in payload and hasattr(game, "real_estate_system"):
                re_data = payload["real_estate"]
                game.real_estate_system.current_residence_id = re_data.get("current_residence_id", "asbury_apt")
                for pid, p_info in re_data.get("properties", {}).items():
                    if pid in game.real_estate_system.properties:
                        prop = game.real_estate_system.properties[pid]
                        prop.is_owned = p_info.get("is_owned", False)
                        prop.is_rented = p_info.get("is_rented", False)
                        prop.home_studio_installed = p_info.get("home_studio_installed", False)
                        prop.studio_gear.clear()
                        for g_info in p_info.get("studio_gear", []):
                            gear = HomeStudioGear(
                                gear_id=g_info.get("gear_id", ""),
                                name=g_info.get("name", "Gear"),
                                category=g_info.get("category", "ACOUSTICS"),
                                cost=g_info.get("cost", 0),
                                quality_boost=g_info.get("quality_boost", 0.1),
                                desc=g_info.get("desc", ""),
                            )
                            prop.studio_gear.append(gear)

            # Tour life deserialization
            if "tour_life" in payload and hasattr(game, "tour_life_simulation"):
                tl_data = payload["tour_life"]
                game.tour_life_simulation.contracts.clear()
                for name, c_info in tl_data.get("contracts", {}).items():
                    contract = BandmateContract(
                        member_name=c_info.get("member_name", name),
                        role=c_info.get("role", "Bassist"),
                        publishing_split_pct=c_info.get("publishing_split_pct", 25.0),
                        weekly_wage=c_info.get("weekly_wage", 150),
                        burnout=c_info.get("burnout", 0.0),
                        satisfaction=c_info.get("satisfaction", 80.0),
                        ego=c_info.get("ego", 50.0),
                    )
                    game.tour_life_simulation.contracts[name] = contract

            # Major label deal deserialization
            if "major_label_deal" in payload and payload["major_label_deal"] and hasattr(game, "major_label_system"):
                mld = payload["major_label_deal"]
                contract = MajorLabelContract(
                    contract_id=mld.get("contract_id", ""),
                    label_name=mld.get("label_name", "Major Label"),
                    city=mld.get("city", "New York City, NY"),
                    headquarters=mld.get("headquarters", "HQ"),
                    advance_amount=mld.get("advance_amount", 250000),
                    artist_royalty_pct=mld.get("artist_royalty_pct", 18.0),
                    recoupable_balance=mld.get("recoupable_balance", 0.0),
                    master_ownership_years=mld.get("master_ownership_years", 10),
                    has_360_deal=mld.get("has_360_deal", False),
                    touring_cut_pct=mld.get("touring_cut_pct", 0.0),
                    merch_cut_pct=mld.get("merch_cut_pct", 0.0),
                    video_fund=mld.get("video_fund", 50000),
                    albums_committed=mld.get("albums_committed", 3),
                    albums_delivered=mld.get("albums_delivered", 0),
                    is_active=mld.get("is_active", True),
                    is_recouped=mld.get("is_recouped", False),
                    is_shelved=mld.get("is_shelved", False),
                )
                game.major_label_system.signed_contract = contract

            # Media & festivals deserialization
            if "media_and_festivals" in payload and hasattr(game, "media_and_festivals_system"):
                mf_data = payload["media_and_festivals"]
                game.media_and_festivals_system.tv_performances_logged = mf_data.get("tv_performances", [])
                game.media_and_festivals_system.festival_sets_logged = mf_data.get("festival_sets", [])

            # Vintage gear deserialization
            if "vintage_gear" in payload and hasattr(game, "vintage_gear_network"):
                owned_ids = set(payload.get("vintage_gear", []))
                game.vintage_gear_network.owned_grails.clear()
                for gid, item in game.vintage_gear_network.catalog.items():
                    if gid in owned_ids:
                        item.is_purchased = True
                        item.is_discovered = True
                        game.vintage_gear_network.owned_grails.append(item)

            # Billboard charts deserialization
            if "billboard_charts" in payload and hasattr(game, "billboard_charts"):
                bc_data = payload["billboard_charts"]
                game.billboard_charts.number_one_milestones = bc_data.get("number_one_milestones", [])
                game.billboard_charts.chart_entries.clear()
                for sid, e_info in bc_data.get("chart_entries", {}).items():
                    entry = BillboardChartEntry(
                        song_id=e_info.get("song_id", sid),
                        title=e_info.get("title", "Track"),
                        artist=e_info.get("artist", "Artist"),
                        current_position=e_info.get("current_position", 100),
                        peak_position=e_info.get("peak_position", 100),
                        weeks_on_chart=e_info.get("weeks_on_chart", 1),
                        points=e_info.get("points", 0.0),
                        is_number_one=e_info.get("is_number_one", False),
                    )
                    game.billboard_charts.chart_entries[sid] = entry

            # v1.4 Sync licensing deserialization
            if "sync_licensing" in payload and hasattr(game, "sync_licensing_system"):
                sync_d = payload["sync_licensing"]
                game.sync_licensing_system.completed_placements_count = sync_d.get("completed_placements_count", 0)
                game.sync_licensing_system.active_placements.clear()
                for pl_info in sync_d.get("active_placements", []):
                    opp_id = pl_info.get("opportunity_id", "hollywood_blockbuster")
                    opp = game.sync_licensing_system.CATALOG.get(opp_id, game.sync_licensing_system.CATALOG["hollywood_blockbuster"])
                    placement = ActiveSyncPlacement(
                        placement_id=pl_info.get("placement_id", "sync_1"),
                        song_id=pl_info.get("song_id", "s1"),
                        song_title=pl_info.get("song_title", "Song"),
                        opportunity=opp,
                        day_placed=pl_info.get("day_placed", 1),
                        days_remaining=pl_info.get("days_remaining", 10),
                        total_fee_earned=pl_info.get("total_fee_earned", 10000),
                    )
                    game.sync_licensing_system.active_placements.append(placement)

            # v1.4 Wellness and vices deserialization
            if "wellness_and_vices" in payload and hasattr(game, "wellness_and_vices_system"):
                w_d = payload["wellness_and_vices"]
                prof = game.wellness_and_vices_system.profile
                prof.addiction_meter = w_d.get("addiction_meter", 0.0)
                prof.vocal_fatigue = w_d.get("vocal_fatigue", 0.0)
                prof.sobriety_streak_days = w_d.get("sobriety_streak_days", 0)
                prof.is_in_rehab = w_d.get("is_in_rehab", False)
                prof.vocal_coaching_level = w_d.get("vocal_coaching_level", 0)
                prof.lifelong_stamina_bonus = w_d.get("lifelong_stamina_bonus", 0.0)

            # v1.4 Finance and legal deserialization
            if "finance_and_legal" in payload and hasattr(game, "finance_and_legal_system"):
                f_d = payload["finance_and_legal"]
                game.finance_and_legal_system.total_taxes_paid = f_d.get("total_taxes_paid", 0)
                game.finance_and_legal_system.last_tax_year = f_d.get("last_tax_year", 2023)
                if f_d.get("hired_cpa"):
                    c_info = f_d["hired_cpa"]
                    game.finance_and_legal_system.hired_cpa = BusinessManagerCPA(
                        name=c_info.get("name", "CPA"),
                        city=c_info.get("city", "Philadelphia, PA"),
                        agency_firm=c_info.get("agency_firm", "Firm"),
                        annual_retainer=c_info.get("annual_retainer", 5000),
                        tax_deduction_efficiency=c_info.get("tax_deduction_efficiency", 0.50),
                    )

            # v1.4 Tour logistics deserialization
            if "tour_logistics" in payload and hasattr(game, "tour_logistics_system"):
                tl_d = payload["tour_logistics"]
                if tl_d.get("tour_bus"):
                    b_info = tl_d["tour_bus"]
                    game.tour_logistics_system.tour_bus = SleeperTourBus(
                        bus_id=b_info.get("bus_id", "luxury_eagle_bus"),
                        model_name=b_info.get("model_name", "Sleeper Bus"),
                        is_leased=b_info.get("is_leased", False),
                        is_owned=b_info.get("is_owned", False),
                        comfort_rating=b_info.get("comfort_rating", 80),
                    )
                game.tour_logistics_system.hired_crew.clear()
                for cid, cr_info in tl_d.get("hired_crew", {}).items():
                    member = TouringCrewMember(
                        crew_id=cr_info.get("crew_id", cid),
                        role_type=cr_info.get("role_type", "FOH_SOUND"),
                        name=cr_info.get("name", "Crew"),
                        weekly_salary=cr_info.get("weekly_salary", 1000),
                        audio_boost=cr_info.get("audio_boost", 0.0),
                        hype_boost=cr_info.get("hype_boost", 0.0),
                        zero_gear_mishaps=cr_info.get("zero_gear_mishaps", False),
                        route_efficiency=cr_info.get("route_efficiency", 0.0),
                    )
                    game.tour_logistics_system.hired_crew[cid] = member

            # v1.4 Gear maintenance deserialization
            if "gear_maintenance" in payload and hasattr(game, "gear_maintenance_system"):
                gm_d = payload["gear_maintenance"]
                m_stat = game.gear_maintenance_system.maintenance_status
                m_stat.condition_pct = gm_d.get("condition_pct", 100.0)
                m_stat.fret_wear_pct = gm_d.get("fret_wear_pct", 0.0)
                m_stat.tube_amp_bias_ok = gm_d.get("tube_amp_bias_ok", True)
                game.gear_maintenance_system.has_overnight_security = gm_d.get("has_overnight_security", False)

            # v1.4 Fan club deserialization
            if "fan_club" in payload and hasattr(game, "fan_club_and_pr_system"):
                fc_d = payload["fan_club"]
                game.fan_club_and_pr_system.is_club_launched = fc_d.get("is_club_launched", False)
                game.fan_club_and_pr_system.accumulated_club_revenue = fc_d.get("accumulated_club_revenue", 0)
                for tid, t_info in fc_d.get("tiers", {}).items():
                    if tid in game.fan_club_and_pr_system.tiers:
                        tier = game.fan_club_and_pr_system.tiers[tid]
                        tier.subscribers_count = t_info.get("subscribers_count", 0)

            # v1.5 Relationships & family deserialization
            if "relationships_and_family" in payload and hasattr(game, "relationships_and_family"):
                rf_d = payload["relationships_and_family"]
                if rf_d.get("partner"):
                    p_info = rf_d["partner"]
                    game.relationships_and_family.partner = RomanticPartner(
                        partner_id=p_info.get("partner_id", "partner_1"),
                        name=p_info.get("name", "Partner"),
                        city=p_info.get("city", "Asbury Park, NJ"),
                        occupation=p_info.get("occupation", "Artist"),
                        personality_trait=p_info.get("personality_trait", "Kind"),
                        affection_level=p_info.get("affection_level", 25.0),
                        relationship_status=p_info.get("relationship_status", "DATING"),
                        shared_home=p_info.get("shared_home", False),
                    )
                if rf_d.get("family"):
                    fam_info = rf_d["family"]
                    game.relationships_and_family.family.parents_relationship = fam_info.get("parents_relationship", 75.0)
                    game.relationships_and_family.family.total_money_sent_home = fam_info.get("total_money_sent_home", 0)
                    game.relationships_and_family.family.homesickness_meter = fam_info.get("homesickness_meter", 10.0)

            # v1.5 Pets deserialization
            if "pets" in payload and hasattr(game, "pets_system"):
                game.pets_system.pets.clear()
                for pet_info in payload.get("pets", []):
                    pet = AdoptedPet(
                        pet_id=pet_info.get("pet_id", "pet_1"),
                        name=pet_info.get("name", "Pet"),
                        species=pet_info.get("species", "DOG"),
                        breed=pet_info.get("breed", "Golden Retriever"),
                        city_adopted=pet_info.get("city_adopted", "Asbury Park, NJ"),
                        happiness=pet_info.get("happiness", 80.0),
                        hunger=pet_info.get("hunger", 20.0),
                        is_tour_companion=pet_info.get("is_tour_companion", True),
                        personality=pet_info.get("personality", "Friendly"),
                    )
                    game.pets_system.pets.append(pet)

            # v1.5 Hobbies deserialization
            if "hobbies" in payload and hasattr(game, "hobbies_and_leisure"):
                game.hobbies_and_leisure.hobbies.clear()
                for hk, h_info in payload.get("hobbies", {}).items():
                    hobby = PersonalHobby(
                        hobby_key=h_info.get("hobby_key", hk),
                        name=h_info.get("name", "Hobby"),
                        skill_level=h_info.get("skill_level", 1),
                        gear_owned=h_info.get("gear_owned", []),
                        total_hours_spent=h_info.get("total_hours_spent", 0),
                        description=h_info.get("description", ""),
                    )
                    game.hobbies_and_leisure.hobbies[hk] = hobby

            # v1.5 Fitness deserialization
            if "fitness" in payload and hasattr(game, "fitness_and_outdoors"):
                fit_d = payload["fitness"]
                f_prof = game.fitness_and_outdoors.profile
                f_prof.physical_conditioning_level = fit_d.get("physical_conditioning_level", 1)
                f_prof.stamina_bonus_earned = fit_d.get("stamina_bonus_earned", 0)
                f_prof.gym_membership_active = fit_d.get("gym_membership_active", False)
                f_prof.workouts_completed = fit_d.get("workouts_completed", 0)
                f_prof.martial_arts_belt = fit_d.get("martial_arts_belt", "White Belt")

            # v1.5 Investments deserialization
            if "investments" in payload and hasattr(game, "investments_and_wealth"):
                inv_d = payload["investments"]
                game.investments_and_wealth.total_dividends_earned = inv_d.get("total_dividends_earned", 0.0)
                game.investments_and_wealth.total_commercial_rent_earned = inv_d.get("total_commercial_rent_earned", 0)
                for sym, s_info in inv_d.get("stocks", {}).items():
                    if sym in game.investments_and_wealth.stocks:
                        stock = game.investments_and_wealth.stocks[sym]
                        stock.shares_owned = s_info.get("shares_owned", 0)
                        stock.total_invested = s_info.get("total_invested", 0)
                        stock.current_value = s_info.get("current_value", 0.0)
                for pk, cp_info in inv_d.get("commercial_properties", {}).items():
                    if pk in game.investments_and_wealth.commercial_properties:
                        cp = game.investments_and_wealth.commercial_properties[pk]
                        cp.is_owned = cp_info.get("is_owned", False)

            # v1.5 Charity deserialization
            if "charity" in payload and hasattr(game, "community_charity"):
                ch_d = payload["charity"]
                game.community_charity.completed_donations = ch_d.get("completed_donations", [])
                game.community_charity.total_donated = ch_d.get("total_donated", 0)

            # v1.6 World Depth deserialization
            if "rivals_and_trends" in payload and hasattr(game, "rival_bands_and_trends"):
                rt_d = payload["rivals_and_trends"]
                for rid, r_info in rt_d.get("rivals", {}).items():
                    if rid in game.rival_bands_and_trends.rivals:
                        r = game.rival_bands_and_trends.rivals[rid]
                        r.fame = r_info.get("fame", r.fame)
                        r.buzz_score = r_info.get("buzz_score", r.buzz_score)
                        r.latest_hit = r_info.get("latest_hit", r.latest_hit)
                if rt_d.get("active_trend"):
                    at = rt_d["active_trend"]
                    game.rival_bands_and_trends.active_trend = CulturalTrendEra(
                        trend_id=at.get("trend_id", "grunge_revival"),
                        name=at.get("name", "Trend"),
                        dominant_genre=at.get("dominant_genre", "Rock"),
                        multiplier=at.get("multiplier", 1.30),
                        days_remaining=at.get("days_remaining", 90),
                        description=at.get("description", ""),
                    )

            if "stage_production" in payload and hasattr(game, "stage_production"):
                sp_d = payload["stage_production"]
                rid = sp_d.get("active_rig_id", "diy_club_rig")
                if rid in game.stage_production.RIG_CATALOG:
                    game.stage_production.active_rig = game.stage_production.RIG_CATALOG[rid]
                game.stage_production.owned_rig_ids = sp_d.get("owned_rig_ids", ["diy_club_rig"])

            if "music_reviews" in payload and hasattr(game, "music_press_reviews"):
                game.music_press_reviews.review_archive.clear()
                for rev_info in payload.get("music_reviews", []):
                    rev = AlbumReview(
                        review_id=rev_info.get("review_id", "rev_1"),
                        album_id=rev_info.get("album_id", "a1"),
                        album_title=rev_info.get("album_title", "Album"),
                        publication=rev_info.get("publication", "Pitchfork"),
                        numeric_score=rev_info.get("numeric_score", 8.0),
                        is_best_new_music=rev_info.get("is_best_new_music", False),
                        review_headline=rev_info.get("review_headline", "Review"),
                        review_blurb=rev_info.get("review_blurb", "Blurb"),
                        day_published=rev_info.get("day_published", 1),
                    )
                    game.music_press_reviews.review_archive.append(rev)

            if "public_persona" in payload and hasattr(game, "press_podcasts"):
                pers_d = payload["public_persona"]
                prof = game.press_podcasts.persona
                prof.auteur_score = pers_d.get("auteur_score", 20)
                prof.working_class_score = pers_d.get("working_class_score", 20)
                prof.maverick_score = pers_d.get("maverick_score", 20)
                prof.total_podcasts_done = pers_d.get("total_podcasts_done", 0)
                game.press_podcasts.podcast_history = pers_d.get("podcast_history", [])

            # v1.7 Full Living NPC deserialization
            if "npcs" in payload and hasattr(game, "npc_system"):
                npc_d = payload["npcs"]
                for nid, n_info in npc_d.items():
                    if nid in game.npc_system.npcs:
                        npc_obj = game.npc_system.npcs[nid]
                        npc_obj.affinity = n_info.get("affinity", npc_obj.affinity)
                        npc_obj.respect = n_info.get("respect", npc_obj.respect)
                        npc_obj.favors_available = n_info.get("favors_available", npc_obj.favors_available)
                        npc_obj.favors_used = n_info.get("favors_used", npc_obj.favors_used)
                        npc_obj.memories = n_info.get("memories", npc_obj.memories)

            # v1.8 Dynamic Traveling AI Musicians deserialization
            if "dynamic_musicians" in payload and hasattr(game, "dynamic_musicians"):
                dm_d = payload["dynamic_musicians"]
                game.dynamic_musicians.musicians.clear()
                for mid, m_info in dm_d.items():
                    musician = AutonomousMusician(
                        artist_id=m_info.get("artist_id", mid),
                        name=m_info.get("name", "Artist"),
                        band_type=m_info.get("band_type", "SOLO_ARTIST"),
                        genre=m_info.get("genre", "Rock"),
                        skill_level=m_info.get("skill_level", 7),
                        fame=m_info.get("fame", 100),
                        funds=m_info.get("funds", 5000),
                        current_city=m_info.get("current_city", "Asbury Park, NJ"),
                        destination_city=m_info.get("destination_city", None),
                        travel_days_left=m_info.get("travel_days_left", 0),
                        status=m_info.get("status", "TOURING"),
                        energy=m_info.get("energy", 85),
                        stress=m_info.get("stress", 20),
                        current_poi_id=m_info.get("current_poi_id", None),
                        tour_itinerary=m_info.get("tour_itinerary", []),
                        affinity_with_player=m_info.get("affinity_with_player", 10.0),
                        co_headlining_with_player=m_info.get("co_headlining_with_player", False),
                        is_signed_to_player_label=m_info.get("is_signed_to_player_label", False),
                    )
                    for t_info in m_info.get("catalog", []):
                        track = DynamicTrack(
                            title=t_info.get("title", "Track"),
                            genre=t_info.get("genre", "Rock"),
                            quality=t_info.get("quality", 0.8),
                            streams=t_info.get("streams", 0),
                        )
                        musician.catalog.append(track)
                    game.dynamic_musicians.musicians[mid] = musician

            # v1.9 International Touring deserialization
            if "international_touring" in payload and hasattr(game, "international_touring"):
                it_d = payload["international_touring"]
                game.international_touring.has_ata_carnet_bond = it_d.get("has_ata_carnet_bond", False)
                game.international_touring.jet_lag_fatigue = it_d.get("jet_lag_fatigue", 0)
                game.international_touring.active_visas.clear()
                for vid, v_info in it_d.get("active_visas", {}).items():
                    visa = InternationalVisa(
                        visa_id=v_info.get("visa_id", vid),
                        territory=v_info.get("territory", "UK"),
                        cost=v_info.get("cost", 600),
                        days_valid=v_info.get("days_valid", 90),
                        is_active=v_info.get("is_active", True),
                        approved_day=v_info.get("approved_day", 1),
                    )
                    game.international_touring.active_visas[vid] = visa

            # v1.9 Physical Vinyl Drops deserialization
            if "physical_vinyl_drops" in payload and hasattr(game, "physical_vinyl_drops"):
                pv_d = payload["physical_vinyl_drops"]
                game.physical_vinyl_drops.total_vinyl_drop_revenue = pv_d.get("total_vinyl_drop_revenue", 0)
                game.physical_vinyl_drops.active_webstore_drops.clear()
                for d_info in pv_d.get("active_webstore_drops", []):
                    drop = DirectVinylDrop(
                        drop_id=d_info.get("drop_id", "drop_1"),
                        album_title=d_info.get("album_title", "Album"),
                        variant_name=d_info.get("variant_name", "Limited Splatter"),
                        units_total=d_info.get("units_total", 150),
                        units_remaining=d_info.get("units_remaining", 0),
                        unit_price=d_info.get("unit_price", 38),
                        total_revenue_earned=d_info.get("total_revenue_earned", 0),
                        is_sold_out=d_info.get("is_sold_out", False),
                    )
                    game.physical_vinyl_drops.active_webstore_drops.append(drop)

                game.physical_vinyl_drops.consignments.clear()
                for c_info in pv_d.get("consignments", []):
                    consign = RecordStoreConsignment(
                        store_name=c_info.get("store_name", "Record Store"),
                        city_name=c_info.get("city_name", "City"),
                        album_title=c_info.get("album_title", "Album"),
                        units_consigned=c_info.get("units_consigned", 25),
                        units_sold=c_info.get("units_sold", 0),
                        wholesale_rate=c_info.get("wholesale_rate", 18),
                        total_payout=c_info.get("total_payout", 0),
                    )
                    game.physical_vinyl_drops.consignments.append(consign)

            # v1.9 Band Creative Tension deserialization
            if "band_creative_tension" in payload and hasattr(game, "band_creative_tension"):
                bct_d = payload["band_creative_tension"]
                game.band_creative_tension.dispute_history.clear()
                for ev_info in bct_d.get("dispute_history", []):
                    ev = CreativeDisputeEvent(
                        event_id=ev_info.get("event_id", "dispute_1"),
                        title=ev_info.get("title", "Dispute"),
                        member_name=ev_info.get("member_name", "Bandmate"),
                        song_title=ev_info.get("song_title", "Track"),
                        description=ev_info.get("description", ""),
                        options=ev_info.get("options", []),
                        resolved=ev_info.get("resolved", True),
                        chosen_option_index=ev_info.get("chosen_option_index", 0),
                    )
                    game.band_creative_tension.dispute_history.append(ev)

            game.last_world_day = current_game_time.day_index()
            if hasattr(game, "GAME_LOG") and hasattr(game.GAME_LOG, "add_log_message"):
                game.GAME_LOG.add_log_message(f"Game loaded successfully from {filepath}.")
            return True
        except Exception as e:
            if hasattr(game, "GAME_LOG") and hasattr(game.GAME_LOG, "add_log_message"):
                game.GAME_LOG.add_log_message(f"Load error: {e}")
            return False
