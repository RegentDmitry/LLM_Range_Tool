import card
from card import Card
import math
from collections import Counter
from card import CardValue
from itertools import combinations
import itertools
from typing import List

def flush_royal(hole_cards, board):
    board_suits = [card.suit for card in board]
    hole_suits = [card.suit for card in hole_cards]

    board_suits_count = Counter(board_suits)
    hole_suits_count = Counter(hole_suits)

    board_suits = [suit for suit, count in board_suits_count.items() if count >= 3]
    hole_suits = [suit for suit, count in hole_suits_count.items() if count >= 2]

    common_suits = set(board_suits).intersection(hole_suits)

    if not common_suits:
        return False

    suit = common_suits.pop()

    hole_cards = [card for card in hole_cards if card.suit == suit]
    board = [card for card in board if card.suit == suit]

    start_vector = create_start_straight_vector(hole_cards, board)
    val = straight_val_recursive(start_vector)

    return val == 14

def create_start_straight_vector(hole_cards, board):
    hole_vals = [card.value for card in hole_cards]
    if 14 in hole_vals:
        hole_vals.append(1)

    board_vals = [card.value for card in board]
    if 14 in board_vals:
        board_vals.append(1)

    start_vector = []
    for i in range(14):
        h = (i + 1) in hole_vals
        b = (i + 1) in board_vals

        if not h and not b:
            start_vector.append(0)
        elif h and not b:
            start_vector.append(1)
        elif not h and b:
            start_vector.append(2)
        else:
            start_vector.append(3)

    return start_vector

def straight_val_recursive(vector):
    if 3 in vector:
        index = vector.index(3)

        vector1 = vector.copy()
        vector1[index] = 1
        s1 = straight_val_recursive(vector1)

        vector2 = vector.copy()
        vector2[index] = 2
        s2 = straight_val_recursive(vector2)

        return max(s1, s2)
    else:
        return straight_val_single(vector)

def straight_val_single(vector):
    has_draw = False
    for i in range(13, 3, -1):
        c1 = c2 = 0
        for j in range(i, i - 5, -1):
            if vector[j] == 1:
                c1 += 1
            if vector[j] == 2:
                c2 += 1
        if c1 == 2 and c2 == 3:
            return i + 1
        if c1 >= 2 and c2 == 2:
            has_draw = True

    return 1 if has_draw else 0

def straight(hole_cards, board):
    start_vector = create_start_straight_vector(hole_cards, board)
    val = straight_val_recursive(start_vector)
    return val > 3

def straight_flush(hole_cards, board):
    board_suits = [card.suit for card in board]
    hole_suits = [card.suit for card in hole_cards]

    board_suits_count = Counter(board_suits)
    hole_suits_count = Counter(hole_suits)

    board_suits = [suit for suit, count in board_suits_count.items() if count >= 3]
    hole_suits = [suit for suit, count in hole_suits_count.items() if count >= 2]

    common_suits = set(board_suits).intersection(hole_suits)

    if not common_suits:
        return False

    suit = common_suits.pop()

    hole_cards = [card for card in hole_cards if card.suit == suit]
    board = [card for card in board if card.suit == suit]

    return straight(hole_cards, board)

def four_of_kind(hole_cards, board):
    board_triple = [value for value, count in Counter(card.value for card in board).items() if count == 3]
    if any(card.value in board_triple for card in hole_cards):
        return True

    board_pairs = [value for value, count in Counter(card.value for card in board).items() if count == 2]
    hole_pairs = [value for value, count in Counter(card.value for card in hole_cards).items() if count == 2]

    if any(pair in board_pairs for pair in hole_pairs):
        return True

    return False

def full_house_pair(hole_cards_values, board_values):
    c3 = 0
    c2 = 0

    m2 = list(combinations(hole_cards_values, 2))
    m3 = list(combinations(board_values, 3))

    for m2_item in m2:
        for m3_item in m3:
            temp = list(m2_item) + list(m3_item)
            dic = {}
            for t in temp:
                if t in dic:
                    dic[t] += 1
                else:
                    dic[t] = 1

            if len(dic) != 2:
                continue

            first, last = dic.items()

            if not ((first[1] == 3 and last[1] == 2) or (first[1] == 2 and last[1] == 3)):
                continue

            cc3 = first[0] if first[1] == 3 else last[0]
            cc2 = first[0] if first[1] == 2 else last[0]

            if cc3 > c3:
                c3 = cc3
                c2 = cc2

            if cc3 == c3 and cc2 > c2:
                c2 = cc2

    if c3 == 0:
        return None

    return c3, c2

def paired(board_values):
    board_list = list(board_values)
    count = len(board_list)
    for i in range(count):
        for j in range(i + 1, count):
            if board_list[i] == board_list[j]:
                return True
    return False

def full_house_by_values(hole_cards_values, board_values):
    is_paired = paired(board_values)
    if is_paired:
        fullhouse_pair = full_house_pair(hole_cards_values, board_values)
        if fullhouse_pair is not None:
            return True
    return False

def full_house(hole_cards, board):
    hole_values = [card.value for card in hole_cards]
    board_values = [card.value for card in board]
    return full_house_by_values(hole_values, board_values)

def flush(hole_cards, board):
    board_suits = [card.suit for card in board]
    hole_suits = [card.suit for card in hole_cards]

    board_suits_counts = {suit: board_suits.count(suit) for suit in set(board_suits)}
    hole_suits_counts = {suit: hole_suits.count(suit) for suit in set(hole_suits)}

    board_suits_with_three_or_more = [suit for suit, count in board_suits_counts.items() if count >= 3]
    hole_suits_with_two_or_more = [suit for suit, count in hole_suits_counts.items() if count >= 2]

    return any(suit in hole_suits_with_two_or_more for suit in board_suits_with_three_or_more)

def top_set(hole_cards, board):
    return top_set_by_values([card.value for card in hole_cards], [card.value for card in board])

def top_set_by_values(hole_cards_values, board_values):
    if paired(board_values):
        return False
    pairs = [value for value, count in Counter(hole_cards_values).items() if count >= 2]
    return max(board_values) in pairs

def middle_set(hole_cards, board):
    return middle_set_by_values([card.value for card in hole_cards], [card.value for card in board])

def middle_set_by_values(hole_cards_values, board_values):
    if paired(board_values):
        return False
    pairs = [value for value, count in Counter(hole_cards_values).items() if count >= 2]
    return any(value in pairs and value != min(board_values) and value != max(board_values) for value in board_values)

def bottom_set(hole_cards, board):
    return bottom_set_by_values([card.value for card in hole_cards], [card.value for card in board])

def bottom_set_by_values(hole_cards_values, board_values):
    if paired(board_values):
        return False
    pairs = [value for value, count in Counter(hole_cards_values).items() if count >= 2]
    return min(board_values) in pairs

def sets(hole_cards, board):
    hole_cards_values = [card.value for card in hole_cards]
    board_values = [card.value for card in board]
    return sets_count(hole_cards_values, board_values)

def sets_count(hole_cards_values, board_values):
    if paired(board_values):
        return 0

    hash_set = set()
    pairs = set()
    for h in hole_cards_values:
        if h not in hash_set:
            hash_set.add(h)
        else:
            pairs.add(h)

    sets = 0
    for b in board_values:
        if b in pairs:
            sets += 1

    return sets

def hasSet(hole_cards, board):
    return sets(hole_cards, board)>0

def two_sets(hole_cards, board):
    return sets(hole_cards, board)>=2

def trips(hole_cards, board):
    if full_house(hole_cards, board):
        return False
    pairs = [value for value, count in Counter(card.value for card in board).items() if count == 2]
    return len([card for card in hole_cards if card.value in pairs]) == 1

def top_two_pairs(hole_cards, board):
    return top_two_pairs_by_values([card.value for card in hole_cards], [card.value for card in board])

def get_pairs(hole_cards, board):
    dict_hole = {}
    for cv in hole_cards:
        if cv in dict_hole:
            dict_hole[cv] += 1
        else:
            dict_hole[cv] = 1
    clear_values = [key for key, value in dict_hole.items() if value == 1]

    dict_board = {}
    for c in board:
        if c in dict_board:
            dict_board[c] += 1
        else:
            dict_board[c] = 1
    clear_board_values = [key for key, value in dict_board.items() if value == 1]

    result = [c for c in clear_values if c in clear_board_values]
    return result

def top_two_pairs_by_values(hole_cards_values, board_values):
    if sets_count(hole_cards_values, board_values) > 0:
        return False

    pairs = get_pairs(hole_cards_values, board_values)
    sorted_board = sorted(board_values, reverse=True)

    return len(pairs) >= 2 and sorted_board[0] in pairs and sorted_board[1] in pairs

def top_and_bottom_pairs(hole_cards, board):
    return top_and_bottom_pairs_by_values([card.value for card in hole_cards], [card.value for card in board])

def top_and_bottom_pairs_by_values(hole_cards_values, board_values):
    if sets_count(hole_cards_values, board_values) > 0:
        return False

    pairs = get_pairs(hole_cards_values, board_values)
    sorted_board = sorted(board_values, reverse=True)

    return len(pairs) >= 2 and sorted_board[0] in pairs and sorted_board[-1] in pairs and sorted_board[1] not in pairs

def bottom_two_pairs(hole_cards, board):
    return bottom_two_pairs_by_values([card.value for card in hole_cards], [card.value for card in board])

def bottom_two_pairs_by_values(hole_cards_values, board_values):
    if sets_count(hole_cards_values, board_values) > 0:
        return False

    pairs = get_pairs(hole_cards_values, board_values)
    sorted_board = sorted(board_values, reverse=False)

    return len(pairs) >= 2 and sorted_board[0] in pairs and sorted_board[1] in pairs and sorted_board[-1] not in pairs

def two_pairs(hole_cards, board):
    return two_pairs_by_values([card.value for card in hole_cards], [card.value for card in board])

def two_pairs_by_values(hole_cards_values, board_values):
    if sets_count(hole_cards_values, board_values) > 0:
        return False

    pairs = get_pairs(hole_cards_values, board_values)
    return len(pairs) >= 2

def over_pair(hole_cards, board):
    return over_pairs([card.value for card in hole_cards], [card.value for card in board]) >= 1

def two_over_pairs(hole_cards, board):
    return over_pairs([card.value for card in hole_cards], [card.value for card in board]) == 2

def over_pairs(hole_cards, board):
    board_max_card = max(board)
    return len(set([card for card in hole_cards if card > board_max_card and hole_cards.count(card) > 1]))

def top_pair(hole_cards, board):
    return top_pair_by_values([card.value for card in hole_cards], [card.value for card in board])

def top_pair_by_values(hole_cards_values, board_values):
    pairs = get_pairs(hole_cards_values, board_values)
    return max(board_values) in pairs

def middle_pair(hole_cards, board):
    return middle_pair_by_values([card.value for card in hole_cards], [card.value for card in board])

def middle_pair_by_values(hole_cards_values, board_values):
    pairs = get_pairs(hole_cards_values, board_values)
    board_min = min(board_values)
    temp = [card for card in board_values if card != board_min]
    if not temp:
        return False

    board_mid = min(temp)
    return len(pairs) == 1 and pairs[0] == board_mid

def bottom_pair(hole_cards, board):
    return bottom_pair_by_values([card.value for card in hole_cards], [card.value for card in board])

def bottom_pair_by_values(hole_cards_values, board_values):
    pairs = get_pairs(hole_cards_values, board_values)
    return len(pairs) == 1 and min(board_values) == pairs[0]

def pair(hole_cards, board):
    return pair_by_values([card.value for card in hole_cards], [card.value for card in board])

def pair_by_values(hole_cards_values, board_values):
    pairs = get_pairs(hole_cards_values, board_values)
    return len(pairs) == 1

def nut_flush(hole_cards, board):
    board_suits = [card.suit for card in board]
    hole_suits = [card.suit for card in hole_cards]

    board_suits_counts = {suit: board_suits.count(suit) for suit in set(board_suits)}
    hole_suits_counts = {suit: hole_suits.count(suit) for suit in set(hole_suits)}

    board_suits_with_three_or_more = [suit for suit, count in board_suits_counts.items() if count >= 3]
    hole_suits_with_two_or_more = [suit for suit, count in hole_suits_counts.items() if count >= 2]

    has_flush = any(suit in hole_suits_with_two_or_more for suit in board_suits_with_three_or_more)

    if not has_flush:
        return False

    flush_suit = next((suit for suit in board_suits if suit in hole_suits), None)
    suit_list = [card.value for card in board if card.suit == flush_suit]
    max_card_value = CardValue._2

    for i in range(14, 1, -1):
        if i not in suit_list:
            max_card_value = CardValue(i)
            break

    return sum(1 for card in hole_cards if card.suit == flush_suit and card.value == max_card_value.value) == 1

def nut_flush2(hole_cards, board):
    board_suits = [card.suit for card in board]
    hole_suits = [card.suit for card in hole_cards]

    board_suits_counts = {suit: board_suits.count(suit) for suit in set(board_suits)}
    hole_suits_counts = {suit: hole_suits.count(suit) for suit in set(hole_suits)}

    has_flush = any(suit for suit in board_suits_counts if board_suits_counts[suit] >= 3 and hole_suits_counts.get(suit, 0) >= 2)
    if not has_flush:
        return False

    flush_suit = next((suit for suit in board_suits_counts if board_suits_counts[suit] >= 3 and hole_suits_counts.get(suit, 0) >= 2), None)
    suit_list = [card.value for card in board if card.suit == flush_suit]
    first_card_value = CardValue._2
    second_card_value = CardValue._2
    first_found = False
    for i in range(14, 1, -1):
        if i not in suit_list:
            if first_found:
                second_card_value = CardValue(i)
                break
            else:
                first_card_value = CardValue(i)
                first_found = True

    return (sum(1 for card in hole_cards if card.suit == flush_suit and card.value == second_card_value.value) == 1 and
            sum(1 for card in hole_cards if card.suit == flush_suit and card.value == first_card_value.value) != 1)

def flush_draw(hole_cards, board):
    board_suits = [card.suit for card in board]
    hole_suits = [card.suit for card in hole_cards]

    board_suits_counts = {suit: board_suits.count(suit) for suit in set(board_suits)}
    hole_suits_counts = {suit: hole_suits.count(suit) for suit in set(hole_suits)}

    return any(suit for suit in board_suits_counts if board_suits_counts[suit] == 2 and hole_suits_counts.get(suit, 0) >= 2)

def nut_flush_draw(hole_cards, board):
    board_suits = [card.suit for card in board]
    hole_suits = [card.suit for card in hole_cards]

    board_suits_counts = {suit: board_suits.count(suit) for suit in set(board_suits)}
    hole_suits_counts = {suit: hole_suits.count(suit) for suit in set(hole_suits)}

    fd = any(suit for suit in board_suits_counts if board_suits_counts[suit] == 2 and hole_suits_counts.get(suit, 0) >= 2)
    if not fd:
        return False

    flush_suit = next((suit for suit in board_suits if hole_suits_counts.get(suit, 0) >= 2), None)
    suit_list = [card.value for card in board if card.suit == flush_suit]
    max_card_value = CardValue._2
    for i in range(14, 1, -1):
        if i not in suit_list:
            max_card_value = CardValue(i)
            break

    return sum(1 for card in hole_cards if card.suit == flush_suit and card.value == max_card_value.value) == 1

def nut_flush_draw2(hole_cards, board):
    board_suits = [card.suit for card in board]
    hole_suits = [card.suit for card in hole_cards]

    board_suits_counts = {suit: board_suits.count(suit) for suit in set(board_suits)}
    hole_suits_counts = {suit: hole_suits.count(suit) for suit in set(hole_suits)}

    fd = any(suit for suit in board_suits_counts if board_suits_counts[suit] == 2 and hole_suits_counts.get(suit, 0) >= 2)
    if not fd:
        return False

    flush_suit = next((suit for suit in board_suits if hole_suits_counts.get(suit, 0) >= 2), None)
    suit_list = [card.value for card in board if card.suit == flush_suit]

    first_card_value = CardValue._2
    second_card_value = CardValue._2
    first_found = False
    for i in range(14, 1, -1):
        if i not in suit_list:
            if first_found:
                second_card_value = CardValue(i)
                break
            else:
                first_card_value = CardValue(i)
                first_found = True

    return (
        sum(1 for card in hole_cards if card.suit == flush_suit and card.value == second_card_value.value) == 1
        and sum(1 for card in hole_cards if card.suit == flush_suit and card.value == first_card_value.value) != 1
    )

def not_nut_flush_draw(hole_cards, board):
    board_suits = [card.suit for card in board]
    hole_suits = [card.suit for card in hole_cards]

    board_suits_counts = {suit: board_suits.count(suit) for suit in set(board_suits)}
    hole_suits_counts = {suit: hole_suits.count(suit) for suit in set(hole_suits)}

    fd = any(suit for suit in board_suits_counts if board_suits_counts[suit] == 2 and hole_suits_counts.get(suit, 0) >= 2)
    if not fd:
        return False

    flush_suit = next((suit for suit in board_suits if hole_suits_counts.get(suit, 0) >= 2), None)
    suit_list = [card.value for card in board if card.suit == flush_suit]

    max_card_value = CardValue._2
    second_card_value = CardValue._2
    first_found = False
    for i in range(14, 1, -1):
        if i not in suit_list:
            if first_found:
                second_card_value = CardValue(i)
                break
            else:
                max_card_value = CardValue(i)
                first_found = True

    return (
        not any(card for card in hole_cards if card.suit == flush_suit and card.value == max_card_value.value)
        and not any(card for card in hole_cards if card.suit == flush_suit and card.value == second_card_value.value)
    )

def tp_tk(hole_cards, board):
    return tp_tk_([card.value for card in hole_cards], [card.value for card in board])

def tp_tk_(hole_cards, board):
    if not top_pair_by_values(hole_cards, board):
        return False

    top_kicker_index = CardValue.A.value
    while top_kicker_index != CardValue._2.value:
        if top_kicker_index not in board:
            break
        top_kicker_index -= 1

    if top_kicker_index == 0:
        return False

    return top_kicker_index in hole_cards

def three_pairs(hole_cards, board):
    return three_pairs_values([card.value for card in hole_cards], [card.value for card in board])

def three_pairs_values(hole_cards, board):
    if sets_count(hole_cards, board) > 0:
        return False

    pairs = get_pairs(hole_cards, board)
    return len(pairs) >= 3

def over_cards(hole_cards, board):
    max_board = max([card.value for card in board])
    cnt = sum(1 for card in hole_cards if card.value > max_board)
    return cnt

def over_card(hole_cards, board):
    return over_cards(hole_cards, board)>0

def over_card1(hole_cards, board):
    return over_cards(hole_cards, board) == 1

def over_card2(hole_cards, board):
    return over_cards(hole_cards, board) == 2

def over_card3(hole_cards, board):
    return over_cards(hole_cards, board) == 3

def over_card4(hole_cards, board):
    return over_cards(hole_cards, board) == 5

def straight_draw(hole_cards, board):
    if len(board) == 5:
        return False

    start_vector = create_start_straight_vector(hole_cards, board)
    return straight_val_recursive(start_vector) == 1

def no_draw(hole_cards, board):
    if flush_draw(hole_cards, board):
        return False

    if straight_draw(hole_cards, board):
        return False

    return True

def straight_draw_single(vector):
    res = 0
    for i in range(10):
        i0 = -1
        c1 = 0
        c2 = 0
        holecards_add = 0
        for j in range(i, i + 5):
            if vector[j] == 0:
                i0 = j
            elif vector[j] == 1:
                c1 += 1
                holecards_add |= 0b10000000000000 >> j
            elif vector[j] == 2:
                c2 += 1
        if c1 == 2 and c2 == 3:
            return 0
        elif c1 == 2 and c2 == 2:
            add = 0b10000000000000 >> i0
            res |= add
        elif c1 == 3 and c2 == 2:
            res |= holecards_add
    return res

def straight_draw_recursive(vector):
    if 3 not in vector:
        return straight_draw_single(vector)
    else:
        index = vector.index(3)
        vector1 = vector[:]
        vector1[index] = 1
        s1 = straight_draw_recursive(vector1)

        vector2 = vector[:]
        vector2[index] = 2
        s2 = straight_draw_recursive(vector2)

        return s1 | s2

def get_value_binary_code(value):
    binary_codes = {
        CardValue._2.value: 0b01000000000000,
        CardValue._3.value: 0b00100000000000,
        CardValue._4.value: 0b00010000000000,
        CardValue._5.value: 0b00001000000000,
        CardValue._6.value: 0b00000100000000,
        CardValue._7.value: 0b00000010000000,
        CardValue._8.value: 0b00000001000000,
        CardValue._9.value: 0b00000000100000,
        CardValue.T.value: 0b00000000010000,
        CardValue.J.value: 0b00000000001000,
        CardValue.Q.value: 0b00000000000100,
        CardValue.K.value: 0b00000000000010,
        CardValue.A.value: 0b00000000000001
    }
    return binary_codes.get(value, 0)

def straight_draw_outs(hole_cards, board):
    if len(board) == 5:
        return 0

    start_vector = create_start_straight_vector(hole_cards, board)
    res = straight_draw_recursive(start_vector)
    if res == 0:
        return 0

    count_outs = 0
    for i in range(14):
        count_outs += 4 if ((0b10000000000000 >> i) & res) > 0 else 0

    for h in hole_cards:
        if (get_value_binary_code(h.value) & res) > 0:
            count_outs -= 1

    for b in board:
        if (get_value_binary_code(b.value) & res) > 0:
            count_outs -= 1

    return count_outs

def gutshot(hole_cards, board):
    return straight_draw_outs(hole_cards, board) == 4

def oesd(hole_cards, board):
    return straight_draw_outs(hole_cards, board) == 8

def wrap(hole_cards, board):
    return straight_draw_outs(hole_cards, board) > 8

def wrap9(hole_cards, board):
    return straight_draw_outs(hole_cards, board) == 9

def wrap12(hole_cards, board):
    return straight_draw_outs(hole_cards, board) == 12

def wrap13(hole_cards, board):
    return straight_draw_outs(hole_cards, board) == 13

def wrap16(hole_cards, board):
    return straight_draw_outs(hole_cards, board) == 16

def wrap17(hole_cards, board):
    return straight_draw_outs(hole_cards, board) == 17

def wrap20(hole_cards, board):
    return straight_draw_outs(hole_cards, board) == 20

def minor_wrap(hole_cards, board):
    return straight_draw_outs(hole_cards, board) > 8 and straight_draw_outs(hole_cards, board) <= 13

def major_wrap(hole_cards, board):
    return straight_draw_outs(hole_cards, board) > 8 and straight_draw_outs(hole_cards, board) >= 16

def flush_blockers(hole_cards, board):
    suit_count = {}
    for card in board:
        if card.suit in suit_count:
            suit_count[card.suit].append(card)
        else:
            suit_count[card.suit] = [card]

    suit_list = [suit for suit, cards in suit_count.items() if len(cards) >= 3]
    if not suit_list:
        return 0

    suit = suit_list[0]
    return sum(1 for hc in hole_cards if hc.suit == suit)

def flush_blocker(hole_cards, board):
    return not flush(hole_cards, board) and flush_blockers(hole_cards, board) > 0

_card_value_list = [CardValue.A, CardValue.K, CardValue.Q, CardValue.J, CardValue.T, CardValue._9, CardValue._8,
                    CardValue._7, CardValue._6, CardValue._5, CardValue._4, CardValue._3, CardValue._2]

def flush_blocker_nut(hole_cards, board):
    return not flush(hole_cards, board) and flush_blocker_nut_(hole_cards, board)
def flush_blocker_nut_(hole_cards, board):
    suit_list = [suit for suit, count in Counter(card.suit for card in board).items() if count >= 3]
    #suit_list = [t.suit for t in board if board.count(t.suit) >= 3]
    if not suit_list:
        return False
    suit = suit_list[0]
    for v in _card_value_list:
        if any(b.suit == suit and b.value == v.value for b in board):
            continue
        return any(hc.suit == suit and hc.value == v.value for hc in hole_cards)
    return False
def flush_blocker_nut2(hole_cards, board):
    return not flush(hole_cards, board) and flush_blocker_nut2_(hole_cards, board)
def flush_blocker_nut2_(hole_cards, board):
    suit_list = [suit for suit, count in Counter(card.suit for card in board).items() if count >= 3]
    #suit_list = [t.suit for t in board if board.count(t.suit) >= 3]
    if not suit_list:
        return False
    suit = suit_list[0]
    skip_first = True
    for v in _card_value_list:
        if any(b.suit == suit and b.value == v.value for b in board):
            continue
        if skip_first:
            skip_first = False
            continue
        return any(hc.suit == suit and hc.value == v.value for hc in hole_cards)
    return False

def flush_draw_blockers(hole_cards, board):
    suit_list = [s for s in set(card.suit for card in board) if sum(1 for card in board if card.suit == s) == 2]
    if not suit_list:
        return 0

    blockers = 0
    for suit in suit_list:
        blockers += sum(1 for hc in hole_cards if hc.suit == suit)

    return blockers

def flush_draw_blocker(hole_cards, board):
    return not flush_draw(hole_cards, board) and flush_draw_blockers(hole_cards, board) > 0

def flush_draw_blocker1(hole_cards, board):
    return not flush_draw(hole_cards, board) and flush_draw_blockers(hole_cards, board) == 1

def flush_draw_blocker2(hole_cards, board):
    return not flush_draw(hole_cards, board) and flush_draw_blockers(hole_cards, board) == 2

def flush_draw_blocker_nut(hole_cards, board):
    suit_list = [s for s in set(card.suit for card in board) if sum(1 for card in board if card.suit == s) == 2]
    if not suit_list:
        return False

    for suit in suit_list:
        for v in _card_value_list:
            if any(b.suit == suit and b.value == v.value for b in board):
                continue

            if any(hc.suit == suit and hc.value == v.value for hc in hole_cards):
                return True

            break

    return False

def flush_draw_blocker_nut2(hole_cards, board):
    suit_list = [s for s in set(card.suit for card in board) if sum(1 for card in board if card.suit == s) == 2]
    if not suit_list:
        return False

    for suit in suit_list:
        skip_first = True
        for v in _card_value_list:
            if any(b.suit == suit and b.value == v.value for b in board):
                continue

            if skip_first:
                skip_first = False
                continue

            if any(hc.suit == suit and hc.value == v.value for hc in hole_cards):
                return True

            break

    return False

def get_possible_straight_blockers(board):
    board_vals = [int(card.value) for card in board]
    if 14 in board_vals:
        board_vals.append(1)

    possible_blockers = set()
    for i in range(14, 3, -1):
        temp_list = []
        c = 0
        for j in range(i, i - 5, -1):
            if j in board_vals:
                c += 1
            else:
                temp_list.append(j)

        if c == 3:
            for t in temp_list:
                possible_blockers.add(t)
        elif c > 3:
            for j in range(i, i - 5, -1):
                possible_blockers.add(j)

    return sorted(possible_blockers, reverse=True)


def get_possible_straight_draw_blockers(board):
    board_vals = [int(card.value) for card in board]
    if 14 in board_vals:
        board_vals.append(1)

    possible_blockers = set()
    for i in range(14, 3, -1):
        temp_list = []
        c = 0
        for j in range(i, i - 5, -1):
            if j in board_vals:
                c += 1
            else:
                temp_list.append(j)

        if c >= 3:
            continue

        if c == 2:
            possible_blockers.update(temp_list)

    return sorted(possible_blockers, reverse=True)

def straight_blockers(hole_cards, board):
    possible_blockers = get_possible_straight_blockers(board)
    return sum(1 for card in hole_cards if int(card.value) in possible_blockers)

def straight_blocker(hole_card, board):
    return straight_blockers(hole_card, board)>0

def straight_blocker1(hole_card, board):
    return straight_blockers(hole_card, board)==1

def straight_blocker2(hole_card, board):
    return straight_blockers(hole_card, board)==2

def straight_blocker3(hole_card, board):
    return straight_blockers(hole_card, board)==3

def straight_blocker4(hole_card, board):
    return straight_blockers(hole_card, board)==4

def get_possible_nuts_straight_blockers(board):
    board_vals = [int(card.value) for card in board]
    if 14 in board_vals:
        board_vals.append(1)

    possible_blockers = set()
    for i in range(14, 3, -1):
        temp_list = []
        c = 0
        for j in range(i, i - 5, -1):
            if j in board_vals:
                c += 1
            else:
                temp_list.append(j)

        if c == 3:
            for t in temp_list:
                possible_blockers.add(t)
            break
        elif c > 3:
            for j in range(i, i - 5, -1):
                possible_blockers.add(j)
            break

    return sorted(possible_blockers, reverse=True)

def straight_blockers_nut(hole_cards, board):
    possible_nut_blockers = get_possible_nuts_straight_blockers(board)
    return sum(1 for card in hole_cards if int(card.value) in possible_nut_blockers)

def straight_blocker_nut(hole_cards, board):
    return straight_blockers_nut(hole_cards, board)>0

def straight_blocker_nut1(hole_cards, board):
    return straight_blockers_nut(hole_cards, board)==1

def straight_blocker_nut2(hole_cards, board):
    return straight_blockers_nut(hole_cards, board)==2

def straight_blocker_nut3(hole_cards, board):
    return straight_blockers_nut(hole_cards, board)==3

def straight_blocker_nut4(hole_cards, board):
    return straight_blockers_nut(hole_cards, board)==4

def straight_draw_blockers(hole_cards, board):
    possible_blockers = get_possible_straight_draw_blockers(board)
    return sum(1 for card in hole_cards if int(card.value) in possible_blockers)

def straight_draw_blocker(hole_cards, board):
    return straight_draw_blockers(hole_cards, board)>0

def straight_draw_blocker1(hole_cards, board):
    return straight_draw_blockers(hole_cards, board)==1

def straight_draw_blocker2(hole_cards, board):
    return straight_draw_blockers(hole_cards, board)==2

def straight_draw_blocker3(hole_cards, board):
    return straight_draw_blockers(hole_cards, board)==3

def straight_draw_blocker4(hole_cards, board):
    return straight_draw_blockers(hole_cards, board)==4

def get_possible_straight_draw_nut_blockers(board):
    board_vals = [int(card.value) for card in board]
    if 14 in board_vals:
        board_vals.append(1)

    possible_blockers = set()
    for i in range(14, 3, -1):
        temp_list = []
        c = 0
        for j in range(i, i - 5, -1):
            if j in board_vals:
                c += 1
            else:
                temp_list.append(j)

        if c >= 3:
            continue

        if c == 2:
            for t in temp_list:
                possible_blockers.add(t)
            break

    return sorted(possible_blockers, reverse=True)

def straight_draw_blockers_nut(hole_cards, board):
    possible_blockers = get_possible_straight_draw_nut_blockers(board)
    return sum(1 for card in hole_cards if int(card.value) in possible_blockers)

def straight_draw_blocker_nut(hole_cards, board):
    return straight_draw_blockers_nut(hole_cards, board)>0

def straight_draw_blocker_nut1(hole_cards, board):
    return straight_draw_blockers_nut(hole_cards, board)==1

def straight_draw_blocker_nut2(hole_cards, board):
    return straight_draw_blockers_nut(hole_cards, board)==2

def straight_draw_blocker_nut3(hole_cards, board):
    return straight_draw_blockers_nut(hole_cards, board)==3

def straight_draw_blocker_nut4(hole_cards, board):
    return straight_draw_blockers_nut(hole_cards, board)==4

def backdoor_straight_draw_single(vector):
    res = 0
    for i in range(10):
        c1 = 0
        c2 = 0
        for j in range(i, i + 5):
            if vector[j] == 1:
                c1 += 1
            elif vector[j] == 2:
                c2 += 1
        if (c1 == 2 or c1 == 3) and (c2 == 3 or c2 == 2):
            return -1
        elif c1 >= 2 and c2 == 1:
            res = 1
    return res

def backdoor_straight_draw_recursive(vector):
    if 3 not in vector:
        return backdoor_straight_draw_single(vector)
    else:
        index = vector.index(3)
        vector1 = list(vector)
        vector1[index] = 1
        s1 = backdoor_straight_draw_recursive(vector1)
        if s1 == -1:
            return -1

        vector2 = list(vector)
        vector2[index] = 2
        s2 = backdoor_straight_draw_recursive(vector2)
        if s2 == -1:
            return -1

        return 1 if s1 == 1 or s2 == 1 else 0

def backdoor_straight_draw(hole_cards, board):
    if len(board) > 3:
        return False

    start_vector = create_start_straight_vector(hole_cards, board)
    return backdoor_straight_draw_recursive(start_vector) > 0

def vec2int(start, count):
    result = 0
    for i in range(start, start + count + 1):
        result += i * int(math.pow(10, i - start))
    return result

def calc_bdsd_single(vector):
    res = set()
    for i in range(10):
        c1 = 0
        c2 = 0
        for j in range(i, i + 5):
            if vector[j] == 1:
                c1 += 1
            elif vector[j] == 2:
                c2 += 1

        if (c1 == 2 or c1 == 3) and (c2 == 3 or c2 == 2):
            return set()
        elif c1 >= 2 and c2 == 1:
            res.add(vec2int(i, 5))

    return res

def calc_bdsd_recursive(vector):
    index = vector.index(3) if 3 in vector else -1
    if index == -1:
        return calc_bdsd_single(vector)
    else:
        vector1 = vector[:]
        vector1[index] = 1
        s1 = calc_bdsd_recursive(vector1)

        vector2 = vector[:]
        vector2[index] = 2
        s2 = calc_bdsd_recursive(vector2)

        s1.update(s2)
        return s1


def backdoor_straight_draw4(hole_cards, board):
    if len(board) > 3:
        return False

    start_vector = create_start_straight_vector(hole_cards, board)
    tmp = calc_bdsd_recursive(start_vector)
    return len(tmp) >= 4

def not_nut_flush(hole_cards, board):
    return flush(hole_cards, board) and not nut_flush(hole_cards, board)

def full_house_n(hole_cards, board):
    return full_house_n_([card.value for card in hole_cards], [card.value for card in board])

def full_house_n_(hole_cards, board):
    is_paired = paired(board)
    if is_paired:
        tmp_full_house_pair = full_house_pair(hole_cards, board)
        top_card = max(board)
        if tmp_full_house_pair:
            return tmp_full_house_pair[0] > tmp_full_house_pair[1] and tmp_full_house_pair[0] >= top_card
    return False

def full_house_nn(hole_cards, board):
    return full_house_nn_([card.value for card in hole_cards], [card.value for card in board])

def full_house_nn_(hole_cards, board):
    is_paired = paired(board)
    if is_paired:
        tmp_full_house_pair = full_house_pair(hole_cards, board)
        if tmp_full_house_pair == None:
            return False
        top_card = max(board)
        if full_house_pair:
            return tmp_full_house_pair[0] < tmp_full_house_pair[1] or tmp_full_house_pair[0] < top_card
    return False

def pocket_pair(hole_cards):
    return (hole_cards[0].value == hole_cards[1].value or
            hole_cards[0].value == hole_cards[2].value or
            hole_cards[0].value == hole_cards[3].value or
            hole_cards[1].value == hole_cards[2].value or
            hole_cards[1].value == hole_cards[3].value or
            hole_cards[2].value == hole_cards[3].value)

def get_possible_straights(board):
    board_vals = [card.value for card in board]
    if 14 in board_vals:
        board_vals.append(1)

    result = []

    for i in range(14, 3, -1):
        c = sum(1 for j in range(i, i - 5, -1) if j in board_vals)
        if c >= 3:
            result.append(i)

    return result

def straight_nut_1(hole_cards, board):
    start_vector = create_start_straight_vector(hole_cards, board)
    val = straight_val_recursive(start_vector)
    if val < 3:
        return False

    possible_straights = get_possible_straights(board)
    return val == possible_straights[0]

def straight_nut_2(hole_cards, board):
    start_vector = create_start_straight_vector(hole_cards, board)
    val = straight_val_recursive(start_vector)
    if val < 3:
        return False

    possible_straights = get_possible_straights(board)
    return len(possible_straights) > 1 and val == possible_straights[1]

def straight_nut_3(hole_cards, board):
    start_vector = create_start_straight_vector(hole_cards, board)
    val = straight_val_recursive(start_vector)
    if val < 3:
        return False

    possible_straights = get_possible_straights(board)
    return len(possible_straights) > 2 and val == possible_straights[2]

def bdfd_count(hole_cards, board):
    if len(board) != 3:
        return 0

    hole_suits = [key for key, group in itertools.groupby(sorted(hole_cards, key=lambda x: x.suit), lambda x: x.suit) if len(list(group)) >= 2]
    if len(hole_suits) == 0:
        return 0

    board_suits = [key for key, group in itertools.groupby(sorted(board, key=lambda x: x.suit), lambda x: x.suit) if len(list(group)) == 1]
    if len(board_suits) == 0:
        return 0

    return sum(1 for suit in hole_suits if suit in board_suits)

def bdfd(hole_cards, board):
    return bdfd_count(hole_cards, board)>0

def bdfd1(hole_cards, board):
    return bdfd_count(hole_cards, board) == 1

def bdfd2(hole_cards, board):
    return bdfd_count(hole_cards, board) == 2
def bdfd_nut(hole_cards, board):
    if len(board) != 3:
        return False

    hole_suits = {}
    for card in hole_cards:
        hole_suits.setdefault(card.suit, []).append(card)

    hole_suits = [max(group, key=lambda x: x.value) for group in hole_suits.values() if len(group) >= 2]
    if not hole_suits:
        return False

    board_suits = {}
    for card in board:
        board_suits.setdefault(card.suit, []).append(card)

    board_candidates = [
        Card(CardValue.K.value if max(group, key=lambda x: x.value).value == CardValue.A.value else CardValue.A.value, suit) for
        suit, group in board_suits.items() if len(group) == 1]
    if not board_candidates:
        return False

    return any(hs in board_candidates for hs in hole_suits)

def get_all_buckets(combo, board):
    boardcards = card.Card.parse_cards(board)
    holecards = card.Card.parse_cards(combo)
    #
    # buckets = { 'RoyalFlush' : flush_royal(holecards, boardcards),
    #             'Flush': flush(holecards, boardcards),
    #             'NutFlush': nut_flush(holecards, boardcards),
    #             'NutFlush2': nut_flush2(holecards, boardcards),
    #             'FlushNotNut': not_nut_flush(holecards, boardcards),
    #             'FlushDraw': flush_draw(holecards, boardcards),
    #             'FlushDrawNotNut': not_nut_flush_draw(holecards, boardcards),
    #             'NutFlushDraw': nut_flush_draw(holecards, boardcards),
    #             'NutFlushDraw2': nut_flush_draw2(holecards, boardcards),
    #             'Set': hasSet(holecards, boardcards),
    #             'TopSet': top_set(holecards, boardcards),
    #             'MiddleSet': middle_set(holecards, boardcards),
    #             'BottomSet': bottom_set(holecards, boardcards),
    #             'TwoSets': two_sets(holecards, boardcards),
    #             'Trips': trips(holecards, boardcards),
    #             'Quads': four_of_kind(holecards, boardcards),
    #             'FullHouse': full_house(holecards, boardcards),
    #             'FullHouseNut': full_house_n(holecards, boardcards),
    #             'FullHouseNotNut': full_house_nn(holecards, boardcards),
    #             'PocketPair': pocket_pair(holecards),
    #             'Pair': pair(holecards, boardcards),
    #             'TopPair': top_pair(holecards, boardcards),
    #             'MiddlePair': middle_pair(holecards, boardcards),
    #             'BottomPair': bottom_pair(holecards, boardcards),
    #             'TpTk': tp_tk(holecards, boardcards),
    #             'TwoPairs': two_pairs(holecards, boardcards),
    #             'TopTwoPairs': top_two_pairs(holecards, boardcards),
    #             'TopAndBottomPairs': top_and_bottom_pairs(holecards, boardcards),
    #             'BottomTwoPairs': bottom_two_pairs(holecards, boardcards),
    #             'ThreePairs': three_pairs(holecards, boardcards),
    #             'OverPair': over_pair(holecards, boardcards),
    #             'TwoOverPairs': two_over_pairs(holecards, boardcards),
    #             'StraightFlush': straight_flush(holecards, boardcards),
    #             'StraightNut': straight_nut_1(holecards, boardcards),
    #             'StraightNut2': straight_nut_2(holecards, boardcards),
    #             'StraightNut3': straight_nut_3(holecards, boardcards),
    #             'Straight': straight(holecards, boardcards),
    #             'StraightDraw': straight_draw(holecards, boardcards),
    #             'NoDraw': no_draw(holecards, boardcards),
    #             'BackdoorStraightDraw': backdoor_straight_draw(holecards, boardcards),
    #             'BackdoorStraightDraw4': backdoor_straight_draw4(holecards, boardcards),
    #             'BackdoorFlushdraw': bdfd(holecards, boardcards),
    #             'BackdoorFlushdraw1': bdfd1(holecards, boardcards),
    #             'BackdoorFlushdraw2': bdfd2(holecards, boardcards),
    #             'BackdoorFlushdrawNut': bdfd_nut(holecards, boardcards),
    #             'Gutshot': gutshot(holecards, boardcards),
    #             'OESD': oesd(holecards, boardcards),
    #             'Wrap': wrap(holecards, boardcards),
    #             'Wrap9': wrap9(holecards, boardcards),
    #             'Wrap12': wrap12(holecards, boardcards),
    #             'Wrap13': wrap13(holecards, boardcards),
    #             'MinorWrap': minor_wrap(holecards, boardcards),
    #             'Wrap16': wrap16(holecards, boardcards),
    #             'Wrap17': wrap17(holecards, boardcards),
    #             'Wrap20': wrap20(holecards, boardcards),
    #             'MajorWrap': major_wrap(holecards, boardcards),
    #             'FlushBlocker': flush_blocker(holecards, boardcards),
    #             'FlushBlockerNut': flush_blocker_nut(holecards, boardcards),
    #             'FlushBlockerNut2': flush_blocker_nut2(holecards, boardcards),
    #             'FlushDrawBlocker': flush_draw_blocker(holecards, boardcards),
    #             'FlushDrawBlocker1': flush_draw_blocker1(holecards, boardcards),
    #             'FlushDrawBlocker2': flush_draw_blocker2(holecards, boardcards),
    #             'FlushDrawBlockerNut': flush_draw_blocker_nut(holecards, boardcards),
    #             'FlushDrawBlockerNut2': flush_draw_blocker_nut2(holecards, boardcards),
    #             'StraightBlocker': straight_blocker(holecards, boardcards),
    #             'StraightBlocker1': straight_blocker1(holecards, boardcards),
    #             'StraightBlocker2': straight_blocker2(holecards, boardcards),
    #             'StraightBlocker3': straight_blocker3(holecards, boardcards),
    #             'StraightBlocker4': straight_blocker4(holecards, boardcards),
    #             'StraightBlockerNut': straight_blocker_nut(holecards, boardcards),
    #             'StraightBlockerNut1': straight_blocker_nut1(holecards, boardcards),
    #             'StraightBlockerNut2': straight_blocker_nut2(holecards, boardcards),
    #             'StraightBlockerNut3': straight_blocker_nut3(holecards, boardcards),
    #             'StraightBlockerNut4': straight_blocker_nut4(holecards, boardcards),
    #             'StraightDrawBlocker': straight_draw_blocker(holecards, boardcards),
    #             'StraightDrawBlocker1': straight_draw_blocker1(holecards, boardcards),
    #             'StraightDrawBlocker2': straight_draw_blocker2(holecards, boardcards),
    #             'StraightDrawBlocker3': straight_draw_blocker3(holecards, boardcards),
    #             'StraightDrawBlocker4': straight_draw_blocker4(holecards, boardcards),
    #             'StraightDrawBlockerNut': straight_draw_blocker_nut(holecards, boardcards),
    #             'StraightDrawBlockerNut1': straight_draw_blocker_nut1(holecards, boardcards),
    #             'StraightDrawBlockerNut2': straight_draw_blocker_nut2(holecards, boardcards),
    #             'StraightDrawBlockerNut3': straight_draw_blocker_nut3(holecards, boardcards),
    #             'StraightDrawBlockerNut4': straight_draw_blocker_nut4(holecards, boardcards)
    #             }

    bucket_vector = [
        1 if flush_royal(holecards, boardcards) else 0,
        1 if flush(holecards, boardcards) else 0,
        1 if nut_flush(holecards, boardcards) else 0,
        1 if nut_flush2(holecards, boardcards) else 0,
        1 if not_nut_flush(holecards, boardcards) else 0,
        1 if flush_draw(holecards, boardcards) else 0,
        1 if not_nut_flush_draw(holecards, boardcards) else 0,
        1 if nut_flush_draw(holecards, boardcards) else 0,
        1 if nut_flush_draw2(holecards, boardcards) else 0,
        1 if hasSet(holecards, boardcards) else 0,
        1 if top_set(holecards, boardcards) else 0,
        1 if middle_set(holecards, boardcards) else 0,
        1 if bottom_set(holecards, boardcards) else 0,
        1 if two_sets(holecards, boardcards) else 0,
        1 if trips(holecards, boardcards) else 0,
        1 if four_of_kind(holecards, boardcards) else 0,
        1 if full_house(holecards, boardcards) else 0,
        1 if full_house_n(holecards, boardcards) else 0,
        1 if full_house_nn(holecards, boardcards) else 0,
        1 if pocket_pair(holecards) else 0,
        1 if pair(holecards, boardcards) else 0,
        1 if top_pair(holecards, boardcards) else 0,
        1 if middle_pair(holecards, boardcards) else 0,
        1 if bottom_pair(holecards, boardcards) else 0,
        1 if tp_tk(holecards, boardcards) else 0,
        1 if two_pairs(holecards, boardcards) else 0,
        1 if top_two_pairs(holecards, boardcards) else 0,
        1 if top_and_bottom_pairs(holecards, boardcards) else 0,
        1 if bottom_two_pairs(holecards, boardcards) else 0,
        1 if three_pairs(holecards, boardcards) else 0,
        1 if over_pair(holecards, boardcards) else 0,
        1 if two_over_pairs(holecards, boardcards) else 0,
        1 if straight_flush(holecards, boardcards) else 0,
        1 if straight_nut_1(holecards, boardcards) else 0,
        1 if straight_nut_2(holecards, boardcards) else 0,
        1 if straight_nut_3(holecards, boardcards) else 0,
        1 if straight(holecards, boardcards) else 0,
        1 if straight_draw(holecards, boardcards) else 0,
        1 if no_draw(holecards, boardcards) else 0,
        1 if backdoor_straight_draw(holecards, boardcards) else 0,
        1 if backdoor_straight_draw4(holecards, boardcards) else 0,
        1 if bdfd(holecards, boardcards) else 0,
        1 if bdfd1(holecards, boardcards) else 0,
        1 if bdfd2(holecards, boardcards) else 0,
        1 if bdfd_nut(holecards, boardcards) else 0,
        1 if gutshot(holecards, boardcards) else 0,
        1 if oesd(holecards, boardcards) else 0,
        1 if wrap(holecards, boardcards) else 0,
        1 if wrap9(holecards, boardcards) else 0,
        1 if wrap12(holecards, boardcards) else 0,
        1 if wrap13(holecards, boardcards) else 0,
        1 if minor_wrap(holecards, boardcards) else 0,
        1 if wrap16(holecards, boardcards) else 0,
        1 if wrap17(holecards, boardcards) else 0,
        1 if wrap20(holecards, boardcards) else 0,
        1 if major_wrap(holecards, boardcards) else 0,
        1 if flush_blocker(holecards, boardcards) else 0,
        1 if flush_blocker_nut(holecards, boardcards) else 0,
        1 if flush_blocker_nut2(holecards, boardcards) else 0,
        1 if flush_draw_blocker(holecards, boardcards) else 0,
        1 if flush_draw_blocker_nut(holecards, boardcards) else 0,
        1 if flush_draw_blocker1(holecards, boardcards) else 0,
        1 if flush_draw_blocker2(holecards, boardcards) else 0,
        1 if flush_draw_blocker_nut2(holecards, boardcards) else 0,
        1 if straight_blocker(holecards, boardcards) else 0,
        1 if straight_blocker1(holecards, boardcards) else 0,
        1 if straight_blocker2(holecards, boardcards) else 0,
        1 if straight_blocker3(holecards, boardcards) else 0,
        1 if straight_blocker4(holecards, boardcards) else 0,
        1 if straight_blocker_nut(holecards, boardcards) else 0,
        1 if straight_blocker_nut1(holecards, boardcards) else 0,
        1 if straight_blocker_nut2(holecards, boardcards) else 0,
        1 if straight_blocker_nut3(holecards, boardcards) else 0,
        1 if straight_blocker_nut4(holecards, boardcards) else 0,
        1 if straight_draw_blocker(holecards, boardcards) else 0,
        1 if straight_draw_blocker1(holecards, boardcards) else 0,
        1 if straight_draw_blocker2(holecards, boardcards) else 0,
        1 if straight_draw_blocker3(holecards, boardcards) else 0,
        1 if straight_draw_blocker4(holecards, boardcards) else 0,
        1 if straight_draw_blocker_nut(holecards, boardcards) else 0,
        1 if straight_draw_blocker_nut1(holecards, boardcards) else 0,
        1 if straight_draw_blocker_nut2(holecards, boardcards) else 0,
        1 if straight_draw_blocker_nut3(holecards, boardcards) else 0,
        1 if straight_draw_blocker_nut4(holecards, boardcards) else 0
    ]

    return bucket_vector

__all__ = ['get_all_buckets']