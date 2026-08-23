import hashlib
from typing import Any

from footballanalyst.ingestion.types import EventSummary, RawMatchData

ATTACKING_ZONE_X_MIN = 48.0
PROGRESSIVE_CARRY_THRESHOLD_METERS = 10.0


class EventSummaryChunker:
    """Chunker that transforms raw StatsBomb match events into EventSummaries."""

    def chunk(self, raw_data: RawMatchData) -> list[EventSummary]:
        """Produce analytical window EventSummaries for a given RawMatchData."""
        match_id = raw_data.match_id
        events = raw_data.events

        chunks = [
            self._build_pressing_summary(match_id, events),
            self._build_xg_by_phase_summary(match_id, events),
            self._build_substitutions_summary(match_id, events),
            self._build_ball_carriers_summary(match_id, events),
            self._build_shot_map_summary(match_id, events),
            self._build_key_passes_summary(match_id, events),
        ]
        shootout_chunk = self._build_penalty_shootout_summary(match_id, events)
        if shootout_chunk:
            chunks.append(shootout_chunk)
        return chunks

    def _generate_chunk_id(self, match_id: int, window: str) -> str:
        raw_key = f"{match_id}_event_summary_{window}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]

    def _build_pressing_summary(
        self, match_id: int, events: list[dict[str, Any]]
    ) -> EventSummary:
        window = "pressing_intensity"
        period_names = {
            1: "First Half",
            2: "Second Half",
            3: "Extra Time 1",
            4: "Extra Time 2",
        }

        def_actions: dict[int, dict[str, int]] = {}
        passes_made: dict[int, dict[str, int]] = {}
        teams: set[str] = set()

        def_types = ("Pressure", "Tackle", "Interception", "Foul Committed")

        for e in events:
            period = e.get("period", 1)
            if period > 4:
                continue

            type_name = e.get("type", {}).get("name")
            team_name = e.get("team", {}).get("name")
            location = e.get("location", [0.0, 0.0])
            x_coord = location[0] if len(location) >= 1 else 0.0

            if not team_name:
                continue
            teams.add(team_name)

            if period not in def_actions:
                def_actions[period] = {}
                passes_made[period] = {}

            # Restrict PPDA calculation to events in attacking 60% of pitch (X >= 48)
            if x_coord >= ATTACKING_ZONE_X_MIN:
                if type_name in def_types:
                    def_actions[period][team_name] = (
                        def_actions[period].get(team_name, 0) + 1
                    )
                elif type_name == "Pass":
                    passes_made[period][team_name] = (
                        passes_made[period].get(team_name, 0) + 1
                    )

        team_list = sorted(teams)
        header = (
            f"Per-Period Attacking 60% Pressing Intensity & PPDA Proxy "
            f"for Match {match_id}:"
        )
        lines = [header]

        for period in sorted(def_actions.keys()):
            p_name = period_names.get(period, f"Period {period}")
            lines.append(f"[{p_name}]")
            for team in team_list:
                actions = def_actions.get(period, {}).get(team, 0)
                opponents = [t for t in team_list if t != team]
                opp_passes = sum(
                    passes_made.get(period, {}).get(opp, 0) for opp in opponents
                )

                if actions > 0:
                    ppda = opp_passes / actions
                    ppda_str = (
                        f"{ppda:.2f} (opponent passes per def action in final 60%)"
                    )
                else:
                    ppda_str = "N/A (0 defensive actions in final 60%)"

                lines.append(
                    f"  - {team}: {actions} defensive actions in attacking zone, "
                    f"PPDA proxy: {ppda_str}"
                )

        text = "\n".join(lines)
        chunk_id = self._generate_chunk_id(match_id, window)
        return EventSummary(
            match_id=match_id, window=window, text=text, chunk_id=chunk_id
        )

    def _build_xg_by_phase_summary(
        self, match_id: int, events: list[dict[str, Any]]
    ) -> EventSummary:
        window = "xg_by_phase"
        xg_by_pattern: dict[str, float] = {}
        shots_by_pattern: dict[str, int] = {}

        for e in events:
            period = e.get("period", 1)
            if period <= 4 and e.get("type", {}).get("name") == "Shot":
                pattern = e.get("play_pattern", {}).get("name", "Regular Play")
                shot_info = e.get("shot", {})
                xg = float(shot_info.get("statsbomb_xg", 0.0))

                xg_by_pattern[pattern] = xg_by_pattern.get(pattern, 0.0) + xg
                shots_by_pattern[pattern] = shots_by_pattern.get(pattern, 0) + 1

        lines = [f"xG Breakdown by Phase of Play for Match {match_id}:"]
        if not shots_by_pattern:
            lines.append("- No shot events recorded in this match.")
        else:
            for pattern, count in sorted(shots_by_pattern.items(), key=lambda x: x[0]):
                total_xg = xg_by_pattern.get(pattern, 0.0)
                lines.append(
                    f"- Phase '{pattern}': {count} shots generated, "
                    f"producing {total_xg:.2f} total xG."
                )

        text = "\n".join(lines)
        chunk_id = self._generate_chunk_id(match_id, window)
        return EventSummary(
            match_id=match_id, window=window, text=text, chunk_id=chunk_id
        )

    def _build_substitutions_summary(
        self, match_id: int, events: list[dict[str, Any]]
    ) -> EventSummary:
        window = "substitutions"
        team_formations: dict[str, str] = {}
        subs: list[str] = []

        for e in events:
            if e.get("type", {}).get("name") == "Starting XI":
                team = e.get("team", {}).get("name", "")
                formation = str(e.get("tactics", {}).get("formation", "Unknown"))
                if team:
                    team_formations[team] = formation

        for e in events:
            type_name = e.get("type", {}).get("name")
            team = e.get("team", {}).get("name", "Unknown")

            if type_name == "Tactical Shift":
                new_formation = str(e.get("tactics", {}).get("formation", ""))
                if new_formation:
                    team_formations[team] = new_formation
            elif type_name == "Substitution":
                minute = e.get("minute", 0)
                player_out = e.get("player", {}).get("name", "Unknown Player")
                sub_info = e.get("substitution", {})
                player_in = sub_info.get("replacement", {}).get(
                    "name", "Unknown Replacement"
                )
                curr_formation = team_formations.get(team, "Unknown Formation")

                subs.append(
                    f"- Minute {minute}': {team} (Formation {curr_formation}) "
                    f"substituted {player_out} OFF for {player_in} ON."
                )

        lines = [f"Substitutions and Tactical Adjustments for Match {match_id}:"]
        if subs:
            lines.extend(subs)
        else:
            lines.append(
                "- No substitutions were recorded during regulation/extra time."
            )

        text = "\n".join(lines)
        chunk_id = self._generate_chunk_id(match_id, window)
        return EventSummary(
            match_id=match_id, window=window, text=text, chunk_id=chunk_id
        )

    def _build_ball_carriers_summary(
        self, match_id: int, events: list[dict[str, Any]]
    ) -> EventSummary:
        window = "top_ball_carriers"
        carrier_prog_dist: dict[str, float] = {}
        carrier_count: dict[str, int] = {}

        for e in events:
            if e.get("type", {}).get("name") == "Carry":
                player = e.get("player", {}).get("name", "Unknown")
                location = e.get("location", [0.0, 0.0])
                carry_end = e.get("carry", {}).get("end_location", [0.0, 0.0])

                if len(location) >= 2 and len(carry_end) >= 2:
                    # Forward dx towards opponent goal line (X = 120)
                    prog_dist = carry_end[0] - location[0]
                else:
                    prog_dist = 0.0

                if prog_dist >= PROGRESSIVE_CARRY_THRESHOLD_METERS:
                    carrier_prog_dist[player] = (
                        carrier_prog_dist.get(player, 0.0) + prog_dist
                    )
                    carrier_count[player] = carrier_count.get(player, 0) + 1

        top_carriers = sorted(
            carrier_prog_dist.items(), key=lambda x: x[1], reverse=True
        )[:5]

        lines = [f"Top Ball Carriers by Progressive Distance for Match {match_id}:"]
        if top_carriers:
            for player, total_dist in top_carriers:
                count = carrier_count.get(player, 0)
                lines.append(
                    f"- {player}: {count} progressive carries (>=10m forward) gaining "
                    f"{total_dist:.1f} meters forward towards goal."
                )
        else:
            lines.append("- No forward progressive carry events (>=10m) recorded.")

        text = "\n".join(lines)
        chunk_id = self._generate_chunk_id(match_id, window)
        return EventSummary(
            match_id=match_id, window=window, text=text, chunk_id=chunk_id
        )

    def _build_shot_map_summary(
        self, match_id: int, events: list[dict[str, Any]]
    ) -> EventSummary:
        window = "shot_map"
        shots: list[str] = []
        team_shots: dict[str, int] = {}
        team_xg: dict[str, float] = {}
        team_goals: dict[str, int] = {}

        p5_shots = [
            e
            for e in events
            if e.get("period") == 5 and e.get("type", {}).get("name") == "Shot"
        ]

        for e in events:
            period = e.get("period", 1)
            if period <= 4 and e.get("type", {}).get("name") == "Shot":
                team = e.get("team", {}).get("name", "Unknown")
                minute = e.get("minute", 0)
                player = e.get("player", {}).get("name", "Unknown")
                shot_info = e.get("shot", {})
                outcome = shot_info.get("outcome", {}).get("name", "Unknown")
                xg = float(shot_info.get("statsbomb_xg", 0.0))

                shot_type = shot_info.get("type", {}).get("name")
                body_part = shot_info.get("body_part", {}).get("name")

                details = [outcome]
                if shot_type:
                    details.append(shot_type)
                if body_part:
                    details.append(body_part)
                details_str = ", ".join(details)

                team_shots[team] = team_shots.get(team, 0) + 1
                team_xg[team] = team_xg.get(team, 0.0) + xg
                if outcome == "Goal":
                    team_goals[team] = team_goals.get(team, 0) + 1

                if outcome == "Goal" or xg >= 0.15:
                    shots.append(
                        f"- Minute {minute}': {player} ({team}) shot [{details_str}], "
                        f"xG: {xg:.2f}"
                    )

        lines = [f"Shot Map & Finishing Summary for Match {match_id}:"]
        for team in sorted(team_shots.keys()):
            s_count = team_shots.get(team, 0)
            tot_xg = team_xg.get(team, 0.0)
            goals = team_goals.get(team, 0)
            lines.append(
                f"- {team}: {goals} goals from {s_count} shots ({tot_xg:.2f} total xG) "
                f"in regulation/extra time."
            )

        if p5_shots:
            pen_goals: dict[str, int] = {}
            for s in p5_shots:
                if s.get("shot", {}).get("outcome", {}).get("name") == "Goal":
                    tm = s.get("team", {}).get("name", "Unknown")
                    pen_goals[tm] = pen_goals.get(tm, 0) + 1
            teams_p5 = list(
                dict.fromkeys(
                    [e.get("team", {}).get("name", "Unknown") for e in p5_shots]
                )
            )
            t1 = teams_p5[0] if len(teams_p5) >= 1 else "Team 1"
            t2 = teams_p5[1] if len(teams_p5) >= 2 else "Team 2"
            p1 = pen_goals.get(t1, 0)
            p2 = pen_goals.get(t2, 0)
            reg1 = team_goals.get(t1, 0)
            reg2 = team_goals.get(t2, 0)
            if p1 > p2:
                w_str = (
                    f"{t1} won {p1} - {p2} on penalties "
                    f"after a {reg1} - {reg2} draw (a.e.t.)"
                )
            elif p2 > p1:
                w_str = (
                    f"{t2} won {p2} - {p1} on penalties "
                    f"after a {reg2} - {reg1} draw (a.e.t.)"
                )
            else:
                w_str = (
                    f"Penalty shootout tied {p1} - {p2} after a {reg1} - {reg2} draw"
                )
            lines.append(f"Match Outcome: {w_str}.")

        if shots:
            lines.append("Key Shot Events:")
            lines.extend(shots[:10])

        text = "\n".join(lines)
        chunk_id = self._generate_chunk_id(match_id, window)
        return EventSummary(
            match_id=match_id, window=window, text=text, chunk_id=chunk_id
        )

    def _build_penalty_shootout_summary(
        self, match_id: int, events: list[dict[str, Any]]
    ) -> EventSummary | None:
        p5_shots = [
            e
            for e in events
            if e.get("period") == 5 and e.get("type", {}).get("name") == "Shot"
        ]
        if not p5_shots:
            return None

        window = "penalty_shootout"
        p1_4_goals: dict[str, int] = {}
        for e in events:
            if (
                e.get("period", 1) <= 4
                and e.get("type", {}).get("name") == "Shot"
                and e.get("shot", {}).get("outcome", {}).get("name") == "Goal"
            ):
                team = e.get("team", {}).get("name", "Unknown")
                p1_4_goals[team] = p1_4_goals.get(team, 0) + 1

        team_pen_goals: dict[str, int] = {}
        kicks: list[str] = []

        for idx, s in enumerate(p5_shots, start=1):
            team = s.get("team", {}).get("name", "Unknown")
            player = s.get("player", {}).get("name", "Unknown")
            shot_info = s.get("shot", {})
            outcome = shot_info.get("outcome", {}).get("name", "Unknown")

            is_goal = outcome == "Goal"
            if is_goal:
                team_pen_goals[team] = team_pen_goals.get(team, 0) + 1
                status_str = "Scored [Goal]"
            else:
                status_str = f"Missed [{outcome}]"

            kicks.append(f"- Kick {idx}: {player} ({team}) - {status_str}")

        teams = list(
            dict.fromkeys([e.get("team", {}).get("name", "Unknown") for e in p5_shots])
        )
        team1 = teams[0] if len(teams) >= 1 else "Team 1"
        team2 = teams[1] if len(teams) >= 2 else "Team 2"
        t1_pens = team_pen_goals.get(team1, 0)
        t2_pens = team_pen_goals.get(team2, 0)
        t1_reg = p1_4_goals.get(team1, 0)
        t2_reg = p1_4_goals.get(team2, 0)

        if t1_pens > t2_pens:
            outcome_str = (
                f"{team1} won {t1_pens} - {t2_pens} on penalties "
                f"after a {t1_reg} - {t2_reg} draw (a.e.t.)"
            )
        elif t2_pens > t1_pens:
            outcome_str = (
                f"{team2} won {t2_pens} - {t1_pens} on penalties "
                f"after a {t2_reg} - {t1_reg} draw (a.e.t.)"
            )
        else:
            outcome_str = (
                f"Penalty shootout tied {t1_pens} - {t2_pens} "
                f"after a {t1_reg} - {t2_reg} draw"
            )

        lines = [
            f"Penalty Shootout Results for Match {match_id}:",
            f"Match Outcome: {outcome_str}.",
            "Kick Sequence:",
            *kicks,
        ]

        text = "\n".join(lines)
        chunk_id = self._generate_chunk_id(match_id, window)
        return EventSummary(
            match_id=match_id, window=window, text=text, chunk_id=chunk_id
        )

    def _build_key_passes_summary(
        self, match_id: int, events: list[dict[str, Any]]
    ) -> EventSummary:
        window = "key_passes"
        key_passes: list[str] = []

        for e in events:
            if e.get("type", {}).get("name") == "Pass":
                pass_info = e.get("pass", {})
                if "shot_assist" in pass_info or "goal_assist" in pass_info:
                    minute = e.get("minute", 0)
                    player = e.get("player", {}).get("name", "Unknown")
                    team = e.get("team", {}).get("name", "Unknown")
                    recipient = pass_info.get("recipient", {}).get("name", "Teammate")
                    is_goal = "goal_assist" in pass_info

                    type_str = "Assist (Goal)" if is_goal else "Key Pass (Shot Assist)"
                    key_passes.append(
                        f"- Minute {minute}': {player} ({team}) -> {recipient} "
                        f"[{type_str}]."
                    )

        lines = [f"Key Passing Sequences and Shot Assists for Match {match_id}:"]
        if key_passes:
            lines.extend(key_passes[:12])
        else:
            lines.append("- No key passes or shot assists recorded.")

        text = "\n".join(lines)
        chunk_id = self._generate_chunk_id(match_id, window)
        return EventSummary(
            match_id=match_id, window=window, text=text, chunk_id=chunk_id
        )
