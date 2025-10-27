import re
from subprocess import run
from typing import List, Tuple, Union

from ..abstractionhelper import is_installed
from ..models.action import Action
from ..models.detailed_entry import DetailedEntry
from ..models.entry import Entry
from ..models.keybinding import Keybinding
from ..models.targets import Target, Targets
from .selector import Selector


class Walker(Selector):
    @staticmethod
    def supported() -> bool:
        return is_installed("walker")

    @staticmethod
    def name() -> str:
        return "walker"

    def show_selection(
        self,
        entries: List[Entry],
        prompt: str,
        show_help_message: bool,
        show_folders: bool,
        keybindings: List[Keybinding],
        additional_args: List[str],
    ) -> Tuple[Union[List[Target], None], Union[Action, None], Union[Entry, None]]:
        parameters = [
            "walker",
            "--width",
            f"{self._calculate_max_width(entries, show_folders) * 15 + max(len(it.username) for it in entries) * 2}",
            "--dmenu",
            "-p",
            prompt,
            *self.__build_parameters_for_keybindings(keybindings),
            *additional_args,
        ]

        # if show_help_message and keybindings:
        #     parameters.extend(self.__format_keybindings_message(keybindings))

        walker = run(
            parameters,
            input="\n".join(self.__format_entries(entries, show_folders)),
            capture_output=True,
            encoding="utf-8",
        )

        print(walker)

        if walker.returncode == 130:
            return None, Action.CANCEL, None
        elif walker.returncode == 0:
            keybinding = keybindings[7]  # 4 - copy password, 5 - copy username
            return_action = keybinding.action
            return_targets = keybinding.targets
        else:
            return_action = None
            return_targets = None

        return return_targets, return_action, self.__parse_formatted_string(walker.stdout)

    def __format_entries(self, entries: List[Entry], show_folders: bool) -> List[str]:
        max_width = self._calculate_max_width(entries, show_folders)
        return [
            f"{self._format_folder(it, show_folders)}{it.name}{self.justify(it, max_width, show_folders)} : {it.username or '~~~'}"
            for it in entries
        ]

    def __parse_formatted_string(self, formatted_string: str) -> Entry:
        match = re.compile("(?:(?P<folder>.+)/)?(?P<name>.*?) +: (?P<username>.*)").search(formatted_string)

        username = match.group("username").strip()
        username = username if username != "~~~" else ""
        return Entry(match.group("name"), match.group("folder"), username)

    def select_target(
        self,
        entry: DetailedEntry,
        show_help_message: bool,
        keybindings: List[Keybinding],
        additional_args: List[str],
    ) -> Tuple[Union[List[Target], None], Union[Action, None]]:
        parameters = [
            "walker",
            "--dmenu",
            # *self.__build_parameters_for_keybindings(keybindings),
            # *additional_args,
        ]

        # if show_help_message and keybindings:
        #     parameters.extend(self.__format_keybindings_message(keybindings))

        rofi = run(
            parameters,
            input="\n".join(self._format_targets_from_entry(entry)),
            capture_output=True,
            encoding="utf-8",
        )

        if rofi.returncode == 130:
            return None, Action.CANCEL
        elif rofi.returncode == 0:
            action = keybindings[1].action
        else:
            action = None

        return (self._extract_targets(rofi.stdout)), action

    def __build_parameters_for_keybindings(self, keybindings: List[Keybinding]) -> List[str]:
        params = []
        for index, keybinding in enumerate(keybindings):
            params.extend([f"-kb-custom-{1 + index}", keybinding.shortcut])

        return params

    def __format_keybindings_message(self, keybindings: List[Keybinding]):
        return [
            "-mesg",
            " | ".join(
                [
                    f"<b>{keybinding.shortcut}</b>: {self.__format_action_and_targets(keybinding)}"
                    for keybinding in keybindings
                ]
            ),
        ]

    def __format_action_and_targets(self, keybinding: Keybinding) -> str:
        if keybinding.targets and Targets.MENU in keybinding.targets:
            return "Menu"
        elif keybinding.action == Action.SYNC:
            return "Sync logins"
        elif keybinding.targets:
            return f"{keybinding.action.value.title()} {', '.join([target.raw for target in keybinding.targets])}"
        else:
            return keybinding.action.value.title()
