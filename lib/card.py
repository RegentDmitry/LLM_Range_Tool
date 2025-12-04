from enum import Enum


class CardValue(Enum):
    A = 14
    K = 13
    Q = 12
    J = 11
    T = 10
    _9 = 9
    _8 = 8
    _7 = 7
    _6 = 6
    _5 = 5
    _4 = 4
    _3 = 3
    _2 = 2
    UNKNOWN = 0

    def __lt__(self, other):
        return self.value < other.value if isinstance(other, CardValue) else NotImplemented


class CardSuit(Enum):
    C = 0
    D = 1
    H = 2
    S = 3

    def __lt__(self, other):
        return self.value < other.value if isinstance(other, CardSuit) else NotImplemented


class Card:
    def __init__(self, value, suit):
        self.value = value
        self.suit = suit

    def __lt__(self, other):
        if self.value != other.value:
            return self.value < other.value
        return self.suit < other.suit

    def __eq__(self, other):
        return self.value == other.value and self.suit == other.suit

    def __repr__(self):
        if isinstance(self.value, int):
            value_str = str(self.value)
        else:
            value_str = self.value.name
        return f"Card({value_str}, {self.suit.name})"

    @staticmethod
    def parse_cards(text):
        cards = []
        while text:
            c = text[0].upper()
            s = text[1].upper()
            if c.isdigit():
                value = int(c)
            elif c in CardValue.__members__:
                value = CardValue[c].value
            else:
                raise ValueError(f"wrong card: {c}")

            if s in CardSuit.__members__:  # Проверяем, есть ли символ в перечислении CardSuit
                suit = CardSuit[s]
            else:
                raise ValueError(f"wrong suit: {s}")

            new_card = Card(value, suit)
            cards.append(new_card)
            text = text[2:]
        return cards


__all__ = ['Card', 'CardSuit', 'CardValue']
