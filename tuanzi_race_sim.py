# -*- coding: utf-8 -*-
"""
鸣潮「小团快跑」蒙特卡洛模拟器。

常用命令：
  python tuanzi_race_sim.py --group A --state fresh --n 50000
  python tuanzi_race_sim.py --group A --state after_upper --n 100000 --rank-stats
  python tuanzi_race_sim.py --group B --state fresh --n 100000 --rank-stats
"""
import argparse
import collections
import random
from dataclasses import dataclass


KING = "布大王团子"
PROP = {3, 11, 16, 23}     # 推进装置
OBST = {10, 28}            # 阻遏装置
RIFT = {6, 20}             # 时空裂隙
FINISH = 32

SKILL_DEVICE_BONUS = "device_bonus"
SKILL_MARK_AHEAD_TWO = "mark_ahead_two"
SKILL_REPEAT_BONUS = "repeat_bonus"
SKILL_WHITE_BIRD = "white_bird"
SKILL_COMEBACK = "comeback"
SKILL_BLESSING = "blessing"
SKILL_MIN_ROLL_BONUS = "min_roll_bonus"
SKILL_FIXED_321 = "fixed_321"
SKILL_COLORFUL = "colorful"
SKILL_GHOST = "ghost"
SKILL_TWO_OR_THREE = "two_or_three"
SKILL_PROFIT_DOUBLE = "profit_double"


@dataclass(frozen=True)
class GroupConfig:
    key: str
    label: str
    dango: tuple
    skills: dict
    skill_names: dict
    skill_desc: dict


@dataclass(frozen=True)
class RaceState:
    key: str
    label: str
    stacks: dict
    progress: dict
    target_progress: int
    king_active: bool = True
    king_join_round: int = 3


@dataclass(frozen=True)
class MoveResult:
    moved: tuple
    old_progress: dict
    new_progress: dict


A_DANGO = (
    "陆·赫斯团子",
    "西格莉卡团子",
    "达妮娅团子",
    "绯雪团子",
    "卡提希娅团子",
    "菲比团子",
)

B_DANGO = (
    "千咲团子",
    "莫宁团子",
    "琳奈团子",
    "爱弥斯团子",
    "守岸人团子",
    "珂莱塔团子",
)

GROUPS = {
    "A": GroupConfig(
        key="A",
        label="A组",
        dango=A_DANGO,
        skills={
            "陆·赫斯团子": SKILL_DEVICE_BONUS,
            "西格莉卡团子": SKILL_MARK_AHEAD_TWO,
            "达妮娅团子": SKILL_REPEAT_BONUS,
            "绯雪团子": SKILL_WHITE_BIRD,
            "卡提希娅团子": SKILL_COMEBACK,
            "菲比团子": SKILL_BLESSING,
        },
        skill_names={
            "陆·赫斯团子": "来颗糖吧",
            "西格莉卡团子": "日冕，帮帮忙！",
            "达妮娅团子": "好事成“双”",
            "绯雪团子": "引路白鸟",
            "卡提希娅团子": "翻盘桥段",
            "菲比团子": "岁主庇佑",
        },
        skill_desc={
            "陆·赫斯团子": "触发推进装置时，额外前进 3 格；触发阻遏装置时，额外后退 1 格。",
            "西格莉卡团子": "每轮标记排名紧邻自己且更高的最多两个团子，被标记团子本回合移动距离 -1，但不会低于 1。",
            "达妮娅团子": "如果本次骰子点数和上一次相同，额外前进 2 格。",
            "绯雪团子": "与布大王团子相遇后，之后每次移动额外前进 1 格。",
            "卡提希娅团子": "每场最多触发 1 次。自身移动结束后如果处于最后一名，则之后每次行动有 60% 概率额外前进 2 格。",
            "菲比团子": "每次移动有 50% 概率额外前进 1 格。",
        },
    ),
    "B": GroupConfig(
        key="B",
        label="B组",
        dango=B_DANGO,
        skills={
            "千咲团子": SKILL_MIN_ROLL_BONUS,
            "莫宁团子": SKILL_FIXED_321,
            "琳奈团子": SKILL_COLORFUL,
            "爱弥斯团子": SKILL_GHOST,
            "守岸人团子": SKILL_TWO_OR_THREE,
            "珂莱塔团子": SKILL_PROFIT_DOUBLE,
        },
        skill_names={
            "千咲团子": "视阈解明",
            "莫宁团子": "精密演算",
            "琳奈团子": "炫彩时刻！",
            "爱弥斯团子": "电子幽灵登场",
            "守岸人团子": "收束的未来",
            "珂莱塔团子": "利润加倍",
        },
        skill_desc={
            "千咲团子": "投骰子时，若投出的结果为本轮所有点数最小之一，则额外前进 2 格。",
            "莫宁团子": "投骰子时，点数固定按 3 / 2 / 1 循环出现。",
            "琳奈团子": "每回合中，20% 概率无法移动，60% 概率按双倍点数移动，20% 概率正常移动。",
            "爱弥斯团子": "每场比赛一次，经过赛程中点后，若前方存在其他非布大王团子，则传送到最近团子顶端。",
            "守岸人团子": "骰子只会掷出 2 或 3。",
            "珂莱塔团子": "28% 概率以骰子的双倍点数前进。",
        },
    ),
}

PRESET_STATES = {
    "A": {
        "after_upper": RaceState(
            key="after_upper",
            label="A组上半场赛后",
            stacks={
                29: ["卡提希娅团子"],
                30: ["陆·赫斯团子", "绯雪团子"],
                31: ["西格莉卡团子", "菲比团子"],
                32: [KING, "达妮娅团子"],
            },
            progress={
                "卡提希娅团子": 29,
                "陆·赫斯团子": 30,
                "绯雪团子": 30,
                "西格莉卡团子": 31,
                "菲比团子": 31,
                "达妮娅团子": 32,
            },
            target_progress=FINISH * 2,
            king_active=True,
        ),
    },
    "B": {},
}

LEGACY_STATE_ALIASES = {
    "after_a_upper": ("A", "after_upper"),
}


def wrap_pos(progress):
    return ((progress - 1) % FINISH) + 1


def clamp_pos(pos):
    return max(1, min(FINISH, pos))


def pos_of(stacks, name):
    for pos, stack in stacks.items():
        if name in stack:
            return pos
    return None


def rank_order(group, stacks, progress):
    """第一名到最后一名。累计进度优先；同进度时，上层团子优先。"""
    arr = []
    order_index = {name: i for i, name in enumerate(group.dango)}
    for _pos, stack in stacks.items():
        for stack_index, name in enumerate(stack):
            if name != KING:
                arr.append((progress[name], stack_index, -order_index[name], name))
    arr.sort(reverse=True)
    return [item[3] for item in arr]


def make_fresh_state(group, start_mode, rng):
    if start_mode == "random":
        stack = list(group.dango)
        rng.shuffle(stack)
    elif start_mode == "skill_bottom_to_top":
        stack = list(group.dango)
    elif start_mode == "skill_top_to_bottom":
        stack = list(reversed(group.dango))
    else:
        raise ValueError(f"未知初始顺序：{start_mode}")

    return {
        "stacks": {1: stack},
        "progress": {name: 1 for name in group.dango},
        "target_progress": FINISH,
        "king_active": False,
        "king_join_round": 3,
    }


def make_preset_state(state):
    return {
        "stacks": {pos: stack[:] for pos, stack in state.stacks.items()},
        "progress": dict(state.progress),
        "target_progress": state.target_progress,
        "king_active": state.king_active,
        "king_join_round": state.king_join_round,
    }


def add_king_to_finish(stacks):
    stacks[FINISH] = [KING] + [name for name in stacks.get(FINISH, []) if name != KING]


def signed_circular_delta(start, end, direction):
    if direction >= 0:
        return (end - start) % FINISH
    return -((start - end) % FINISH)


def device_step(pos, delta, circular):
    return wrap_pos(pos + delta) if circular else clamp_pos(pos + delta)


def move_king_position(start, dist, direction, circular):
    pos = wrap_pos(start + direction * dist) if circular else clamp_pos(start + direction * dist)
    for _ in range(10):
        if pos in RIFT:
            break
        if pos in PROP:
            pos = device_step(pos, 1, circular)
            continue
        if pos in OBST:
            pos = device_step(pos, -1, circular)
            continue
        break
    return pos


def move_piece(group, stacks, progress, mover, dist, direction, rng, target_progress):
    """移动 mover；普通团子使用累计进度，布大王使用物理格。"""
    if dist <= 0:
        return MoveResult((), {}, {})

    start = pos_of(stacks, mover)
    stack = stacks[start]
    idx = stack.index(mover)
    segment = stack[idx:]
    stacks[start] = stack[:idx]
    if not stacks[start]:
        del stacks[start]

    old_progress = {name: progress[name] for name in segment if name != KING}
    circular = target_progress > FINISH

    if mover == KING:
        pos = move_king_position(start, dist, direction, circular)
        delta = signed_circular_delta(start, pos, direction) if circular else pos - start
        finished = False
    else:
        start_progress = progress[mover]
        final_progress = start_progress + dist
        finished = final_progress >= target_progress
        if finished:
            final_progress = target_progress

        pos = wrap_pos(final_progress)
        for _ in range(10):
            if finished or pos in RIFT:
                break
            skill = group.skills.get(mover)
            if pos in PROP:
                final_progress += 1 + (3 if skill == SKILL_DEVICE_BONUS and direction == 1 else 0)
                finished = final_progress >= target_progress
                if finished:
                    final_progress = target_progress
                pos = wrap_pos(final_progress)
                continue
            if pos in OBST:
                final_progress = max(1, final_progress - (1 + (1 if skill == SKILL_DEVICE_BONUS and direction == 1 else 0)))
                pos = wrap_pos(final_progress)
                continue
            break
        delta = final_progress - start_progress

    new_progress = {}
    for name in segment:
        if name == KING:
            continue
        progress[name] += delta
        if progress[name] >= target_progress:
            progress[name] = target_progress
            finished = True
        new_progress[name] = progress[name]

    target = stacks.get(pos, [])
    if mover == KING:
        regular_segment = [name for name in segment if name != KING]
        new_stack = [KING] + target + regular_segment
    else:
        new_stack = target + segment
        if KING in new_stack:
            new_stack = [KING] + [name for name in new_stack if name != KING]

    if pos in RIFT:
        regulars = [name for name in new_stack if name != KING]
        rng.shuffle(regulars)
        new_stack = ([KING] if KING in new_stack else []) + regulars

    stacks[pos] = new_stack
    return MoveResult(tuple(old_progress), old_progress, new_progress)


def roll_for(group, name, normal_faces, runtime, rng):
    skill = group.skills.get(name)
    if name == KING:
        return rng.randint(1, 6)
    if skill == SKILL_FIXED_321:
        cycle = (3, 2, 1)
        idx = runtime["cycle_index"][name]
        runtime["cycle_index"][name] += 1
        return cycle[idx % len(cycle)]
    if skill == SKILL_TWO_OR_THREE:
        return rng.choice((2, 3))
    return rng.choice(normal_faces)


def marked_this_round(group, stacks, progress):
    marked = set()
    ranks = rank_order(group, stacks, progress)
    for name in group.dango:
        if group.skills.get(name) != SKILL_MARK_AHEAD_TWO:
            continue
        idx = ranks.index(name)
        marked.update(ranks[max(0, idx - 2):idx])
    return marked


def movement_distance(group, name, base, rolls, marked, runtime, rng):
    skill = group.skills.get(name)
    dist = base

    if skill == SKILL_COLORFUL:
        roll = rng.random()
        if roll < 0.20:
            dist = 0
        elif roll < 0.80:
            dist = base * 2
    elif skill == SKILL_PROFIT_DOUBLE and rng.random() < 0.28:
        dist = base * 2

    if skill == SKILL_BLESSING and rng.random() < 0.5:
        dist += 1

    if skill == SKILL_REPEAT_BONUS:
        if runtime["prev_roll"][name] is not None and base == runtime["prev_roll"][name]:
            dist += 2

    if skill == SKILL_WHITE_BIRD and name in runtime["white_met_king"]:
        dist += 1

    if skill == SKILL_COMEBACK and name in runtime["comeback_active"] and rng.random() < 0.6:
        dist += 2

    if skill == SKILL_MIN_ROLL_BONUS and base == min(rolls.values()):
        dist += 2

    runtime["prev_roll"][name] = base

    if dist > 0 and name in marked:
        dist = max(1, dist - 1)
    return dist


def remove_single(stacks, name):
    pos = pos_of(stacks, name)
    if pos is None:
        return None
    stack = stacks[pos]
    stack.remove(name)
    if not stack:
        del stacks[pos]
    return pos


def teleport_to_nearest_ahead(group, stacks, progress, name):
    ahead = [
        (progress[other] - progress[name], progress[other], other)
        for other in group.dango
        if other != name and progress[other] > progress[name]
    ]
    if not ahead:
        return

    _distance, target_progress, target_name = min(ahead)
    target_pos = pos_of(stacks, target_name)
    remove_single(stacks, name)
    stacks[target_pos] = stacks.get(target_pos, []) + [name]
    if KING in stacks[target_pos]:
        stacks[target_pos] = [KING] + [item for item in stacks[target_pos] if item != KING]
    progress[name] = target_progress


def apply_after_move_hooks(group, stacks, progress, move_result, runtime, target_progress):
    midpoint = target_progress - FINISH // 2
    for name in move_result.moved:
        if group.skills.get(name) != SKILL_GHOST or name in runtime["ghost_used"]:
            continue
        old = move_result.old_progress[name]
        new = move_result.new_progress[name]
        if old < midpoint <= new:
            runtime["ghost_used"].add(name)
            teleport_to_nearest_ahead(group, stacks, progress, name)


def update_meeting_skills(group, stacks, runtime):
    king_pos = pos_of(stacks, KING)
    if king_pos is None:
        return
    for name in group.dango:
        if group.skills.get(name) == SKILL_WHITE_BIRD and pos_of(stacks, name) == king_pos:
            runtime["white_met_king"].add(name)


def update_comeback_skill(group, stacks, progress, mover, runtime):
    if group.skills.get(mover) != SKILL_COMEBACK or mover in runtime["comeback_triggered"]:
        return
    if rank_order(group, stacks, progress)[-1] == mover:
        runtime["comeback_triggered"].add(mover)
        runtime["comeback_active"].add(mover)


def reset_king_position(group, stacks, progress):
    last = rank_order(group, stacks, progress)[-1]
    king_pos = pos_of(stacks, KING)
    if king_pos is None:
        return
    if king_pos != pos_of(stacks, last):
        stacks[king_pos].remove(KING)
        if not stacks[king_pos]:
            del stacks[king_pos]
        add_king_to_finish(stacks)
    elif stacks[king_pos][0] != KING:
        stacks[king_pos] = [KING] + [name for name in stacks[king_pos] if name != KING]


def simulate_one(group, state_key, start_mode, normal_faces, order_mode, rng):
    if state_key == "fresh":
        state = make_fresh_state(group, start_mode, rng)
    else:
        state = make_preset_state(PRESET_STATES[group.key][state_key])

    stacks = state["stacks"]
    progress = state["progress"]
    target_progress = state["target_progress"]
    king_active = state["king_active"]
    king_join_round = state["king_join_round"]

    runtime = {
        "prev_roll": {name: None for name in group.dango},
        "cycle_index": collections.Counter(),
        "white_met_king": set(),
        "comeback_triggered": set(),
        "comeback_active": set(),
        "ghost_used": set(),
    }

    fixed_action = None
    if order_mode == "fixed_initial":
        fixed_action = list(group.dango)
        rng.shuffle(fixed_action)

    round_no = 0
    while round_no < 200:
        round_no += 1
        if round_no == king_join_round and not king_active:
            add_king_to_finish(stacks)
            king_active = True

        participants = list(group.dango) + ([KING] if king_active else [])
        rolls = {name: roll_for(group, name, normal_faces, runtime, rng) for name in participants}

        if order_mode == "dice_sorted":
            action = participants[:]
            rng.shuffle(action)
            action.sort(key=lambda name: rolls[name], reverse=True)
        elif order_mode == "fixed_initial":
            action = fixed_action[:]
            if king_active:
                action.insert(rng.randrange(len(action) + 1), KING)
        else:
            action = participants[:]
            rng.shuffle(action)

        marked = marked_this_round(group, stacks, progress)

        for name in action:
            if name == KING:
                move_result = move_piece(group, stacks, progress, KING, rolls[name], -1, rng, target_progress)
            else:
                dist = movement_distance(group, name, rolls[name], rolls, marked, runtime, rng)
                move_result = move_piece(group, stacks, progress, name, dist, 1, rng, target_progress)

            apply_after_move_hooks(group, stacks, progress, move_result, runtime, target_progress)
            update_meeting_skills(group, stacks, runtime)
            update_comeback_skill(group, stacks, progress, name, runtime)

            if max(progress.values()) >= target_progress:
                return rank_order(group, stacks, progress), round_no

        if king_active:
            reset_king_position(group, stacks, progress)

    return rank_order(group, stacks, progress), round_no


def run_simulation(group, state_key, n, seed, normal_faces, start_mode, order_mode):
    rng = random.Random(seed)
    winner_counter = collections.Counter()
    rank_counter = {name: collections.Counter() for name in group.dango}
    round_sum = 0

    for _ in range(n):
        ranks, rounds = simulate_one(group, state_key, start_mode, normal_faces, order_mode, rng)
        winner_counter[ranks[0]] += 1
        round_sum += rounds
        for i, name in enumerate(ranks, start=1):
            rank_counter[name][i] += 1

    return winner_counter, rank_counter, round_sum / n


def resolve_group_and_state(group_key, state_key):
    if state_key in LEGACY_STATE_ALIASES:
        alias_group, alias_state = LEGACY_STATE_ALIASES[state_key]
        if group_key != alias_group:
            raise SystemExit(f"--state {state_key} 属于 {alias_group} 组，不能和 --group {group_key} 同时使用。")
        return GROUPS[alias_group], alias_state

    if group_key not in GROUPS:
        raise SystemExit(f"未知组别：{group_key}。可选：{', '.join(sorted(GROUPS))}")

    group = GROUPS[group_key]
    if state_key == "fresh" or state_key in PRESET_STATES.get(group.key, {}):
        return group, state_key

    available = ["fresh"] + sorted(PRESET_STATES.get(group.key, {}))
    raise SystemExit(f"{group.label} 没有状态 {state_key}。可选：{', '.join(available)}")


def print_report(group, state_key, n, dice_label, start_mode, order_mode, avg_round, winner_counter, rank_counter, rank_stats):
    target = "finish" if state_key == "fresh" else "next_finish"
    print(
        f"N={n}, group={group.key}, dice={dice_label}, state={state_key}, "
        f"start={start_mode}, order={order_mode}, target={target}, avg_round={avg_round:.2f}"
    )
    print("冠军率:")
    for name, count in winner_counter.most_common():
        print(f"{name}: {count / n * 100:.2f}%")

    if not rank_stats:
        return

    print("前4率:")
    top4_rates = []
    for name in group.dango:
        top4 = sum(rank_counter[name][i] for i in range(1, 5))
        top4_rates.append((top4, name))
    for top4, name in sorted(top4_rates, reverse=True):
        print(f"{name}: {top4 / n * 100:.2f}%")

    print("平均名次:")
    avg_ranks = []
    for name in group.dango:
        rank_sum = sum(i * rank_counter[name][i] for i in range(1, 7))
        avg_ranks.append((rank_sum / n, name))
    for avg_rank, name in sorted(avg_ranks):
        print(f"{name}: {avg_rank:.2f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", choices=sorted(GROUPS), default="A")
    parser.add_argument("--state", default="fresh")
    parser.add_argument("--n", type=int, default=50000)
    parser.add_argument("--seed", type=int, default=20260508)
    parser.add_argument("--dice", choices=["1-3", "1-6"], default="1-3")
    parser.add_argument("--start", choices=["random", "skill_bottom_to_top", "skill_top_to_bottom"], default="random")
    parser.add_argument("--order", choices=["random_each_round", "fixed_initial", "dice_sorted"], default="random_each_round")
    parser.add_argument("--rank-stats", action="store_true")
    args = parser.parse_args()

    group, state_key = resolve_group_and_state(args.group, args.state)
    faces = tuple(range(1, 4)) if args.dice == "1-3" else tuple(range(1, 7))
    winner_counter, rank_counter, avg_round = run_simulation(
        group=group,
        state_key=state_key,
        n=args.n,
        seed=args.seed,
        normal_faces=faces,
        start_mode=args.start,
        order_mode=args.order,
    )
    print_report(
        group=group,
        state_key=state_key,
        n=args.n,
        dice_label=args.dice,
        start_mode=args.start,
        order_mode=args.order,
        avg_round=avg_round,
        winner_counter=winner_counter,
        rank_counter=rank_counter,
        rank_stats=args.rank_stats,
    )


if __name__ == "__main__":
    main()
