# -*- coding: utf-8 -*-
"""
鸣潮「团子快跑」蒙特卡洛模拟器
说明：只用标准库，直接运行：python tuanzi_race_sim.py --n 50000
默认假设：普通团子骰子为1/2/3等概率；布大王团子骰子为1-6；初始堆叠随机；每回合行动顺序随机。
"""
import argparse
import collections
import random

CANDY = "陆·赫斯团子"
CORONA = "西格莉卡团子"
DOUBLE = "达妮娅团子"
WHITE_BIRD = "绯雪团子"
COMEBACK = "卡提希娅团子"
BLESSING = "菲比团子"

DANGO = [CANDY, CORONA, DOUBLE, WHITE_BIRD, COMEBACK, BLESSING]
KING = "布大王团子"
PROP = {3, 11, 16, 23}     # 推进装置
OBST = {10, 28}            # 阻遏装置
RIFT = {6, 20}             # 时空裂隙
FINISH = 32

FIXED_ORDERS = {
    # bottom -> top
    "skill_bottom_to_top": DANGO[:],
    "skill_top_to_bottom": list(reversed(DANGO)),
}

def rank_order(stacks):
    """返回当前名次：第一名到最后一名。位置更靠前优先；同格时上层优先。"""
    arr = []
    for pos, stack in stacks.items():
        for i, name in enumerate(stack):
            if name != KING:
                arr.append((pos, i, name))
    arr.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [x[2] for x in arr]

def pos_of(stacks, name):
    for pos, stack in stacks.items():
        if name in stack:
            return pos
    return None

def move(stacks, mover, dist, direction, rng):
    """移动 mover。规则：移动者会带走自己及其上方团子；到同格后叠在最上方。"""
    start = pos_of(stacks, mover)
    stack = stacks[start]
    idx = stack.index(mover)
    segment = stack[idx:]
    stacks[start] = stack[:idx]
    if not stacks[start]:
        del stacks[start]

    pos = start + direction * dist
    pos = max(1, min(FINISH, pos))

    # 机关连锁：推进/阻遏改变最终落点；裂隙只随机化堆叠顺序，不再继续推进。
    for _ in range(10):
        if pos in RIFT:
            break
        if pos in PROP:
            # 「来颗糖吧」：触发推进时，普通+1基础上再额外+3。
            delta = 1 + (3 if mover == CANDY and direction == 1 else 0)
            pos = min(FINISH, pos + delta)
            continue
        if pos in OBST:
            # 「来颗糖吧」：触发阻遏时，普通-1基础上再额外-1。
            delta = -1 - (1 if mover == CANDY and direction == 1 else 0)
            pos = max(1, pos + delta)
            continue
        break

    target = stacks.get(pos, [])
    if mover == KING:
        # 布大王团子始终在底部；若它带着普通团子移动，普通团子落在目标堆叠上方。
        regular_segment = [x for x in segment if x != KING]
        new_stack = [KING] + target + regular_segment
    else:
        new_stack = target + segment
        if KING in new_stack:
            new_stack = [KING] + [x for x in new_stack if x != KING]

    if pos in RIFT:
        regs = [x for x in new_stack if x != KING]
        rng.shuffle(regs)
        new_stack = ([KING] if KING in new_stack else []) + regs

    stacks[pos] = new_stack

def simulate_one(rng, normal_faces=(1, 2, 3), start_order=None, order_mode="random_each_round"):
    # 初始堆叠 bottom -> top
    if start_order is None:
        init = DANGO[:]
        rng.shuffle(init)
    else:
        init = list(start_order)
    stacks = {1: init}

    prev_roll = {d: None for d in DANGO}
    flip_triggered = False
    flip_active = False
    white_met_king = False
    king_active = False

    fixed_action = None
    if order_mode == "fixed_initial":
        fixed_action = DANGO[:]
        rng.shuffle(fixed_action)

    round_no = 0
    while round_no < 200:
        round_no += 1
        if round_no == 3 and not king_active:
            stacks[FINISH] = [KING] + stacks.get(FINISH, [])
            king_active = True

        participants = DANGO[:] + ([KING] if king_active else [])
        rolls = {}

        if order_mode == "dice_sorted":
            for p in participants:
                rolls[p] = rng.randint(1, 6) if p == KING else rng.choice(normal_faces)
            action = participants[:]
            rng.shuffle(action)
            action.sort(key=lambda p: rolls[p], reverse=True)
        elif order_mode == "fixed_initial":
            action = fixed_action[:]
            if king_active:
                action.insert(rng.randrange(len(action) + 1), KING)
            for p in participants:
                rolls[p] = rng.randint(1, 6) if p == KING else rng.choice(normal_faces)
        else:
            action = participants[:]
            rng.shuffle(action)
            for p in participants:
                rolls[p] = rng.randint(1, 6) if p == KING else rng.choice(normal_faces)

        # 「日冕，帮帮忙！」：每轮开始标记自己前面紧邻的最多两个团子。
        ranks = rank_order(stacks)
        idx = ranks.index(CORONA)
        marked = set(ranks[max(0, idx - 2):idx])

        for p in action:
            if p == KING:
                move(stacks, KING, rolls[p], -1, rng)
            else:
                base = rolls[p]
                bonus = 0

                if p == BLESSING and rng.random() < 0.5:
                    bonus += 1

                if p == DOUBLE:
                    if prev_roll[p] is not None and base == prev_roll[p]:
                        bonus += 2
                    prev_roll[p] = base
                else:
                    prev_roll[p] = base

                if p == WHITE_BIRD and white_met_king:
                    bonus += 1

                if p == COMEBACK and flip_active and rng.random() < 0.6:
                    bonus += 2

                dist = base + bonus
                if p in marked:
                    dist = max(1, dist - 1)

                move(stacks, p, dist, 1, rng)

            # 绯雪团子遇到布大王团子后，之后自己的行动额外+1。
            if king_active and pos_of(stacks, WHITE_BIRD) == pos_of(stacks, KING):
                white_met_king = True

            # 翻盘桥段：自己移动结束后若最后一名，之后每次行动60%额外+2。
            if p == COMEBACK and not flip_triggered:
                if rank_order(stacks)[-1] == COMEBACK:
                    flip_triggered = True
                    flip_active = True

            # 有团子到达或越过终点，立即按当前堆叠结算冠军。
            if max(pos_of(stacks, d) for d in DANGO) >= FINISH:
                return rank_order(stacks)[0], round_no

        # 回合结束：布大王团子若没有和最后一名普通团子在一起，则回到终点。
        if king_active:
            last = rank_order(stacks)[-1]
            king_pos = pos_of(stacks, KING)
            if king_pos is not None and king_pos != pos_of(stacks, last):
                stacks[king_pos].remove(KING)
                if not stacks[king_pos]:
                    del stacks[king_pos]
                stacks[FINISH] = [KING] + [x for x in stacks.get(FINISH, []) if x != KING]
            elif king_pos is not None and stacks[king_pos][0] != KING:
                stacks[king_pos] = [KING] + [x for x in stacks[king_pos] if x != KING]

    return rank_order(stacks)[0], round_no

def run(n, seed, normal_faces, start_order, order_mode):
    rng = random.Random(seed)
    counter = collections.Counter()
    round_sum = 0
    for _ in range(n):
        winner, rounds = simulate_one(rng, normal_faces, start_order, order_mode)
        counter[winner] += 1
        round_sum += rounds
    return counter, round_sum / n

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=50000)
    parser.add_argument("--seed", type=int, default=20260508)
    parser.add_argument("--dice", choices=["1-3", "1-6"], default="1-3")
    parser.add_argument("--start", choices=["random", "skill_bottom_to_top", "skill_top_to_bottom"], default="random")
    parser.add_argument("--order", choices=["random_each_round", "fixed_initial", "dice_sorted"], default="random_each_round")
    args = parser.parse_args()

    faces = tuple(range(1, 4)) if args.dice == "1-3" else tuple(range(1, 7))
    start_order = None if args.start == "random" else FIXED_ORDERS[args.start]
    counter, avg_round = run(args.n, args.seed, faces, start_order, args.order)

    print(f"N={args.n}, dice={args.dice}, start={args.start}, order={args.order}, avg_round={avg_round:.2f}")
    for name, count in counter.most_common():
        print(f"{name}: {count / args.n * 100:.2f}%")

if __name__ == "__main__":
    main()
