from enum import Enum


class ChannelNames(Enum):
    vc_name = "VC-NAME"
    username = "USERNAME"
    increment = "INCREMENT"
    custom = "CUSTOM"

    def __str__(self):
        return self.value

    def __eq__(self, other):
        return self.value == other


