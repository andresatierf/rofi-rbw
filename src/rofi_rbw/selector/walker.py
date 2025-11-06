import re
from subprocess import run
from typing import List, Tuple, Union

from ..abstractionhelper import is_installed
from ..models.action import Action
from ..models.detailed_entry import DetailedEntry
from ..models.entry import Entry
from ..models.keybinding import Keybinding
from ..models.targets import Target, Targets, TypeTarget
from .selector import Selector


class Walker(Selector):
    select_keybind = Keybinding("", None, [TypeTarget("Select")])

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

        if walker.returncode == 130:
            return None, Action.CANCEL, None
        elif walker.returncode == 0:
            keybinding = self.__select_keybindings(prompt, keybindings)
            return_action = keybinding.action if keybinding else None
            return_targets = keybinding.targets if keybinding else None
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

    def __select_keybindings(self, prompt: str, keybindings: List[Keybinding]) -> Keybinding:
        parameters = [
            "walker",
            "--dmenu",
            "-p",
            prompt,
        ]

        walker = run(
            parameters,
            input="\n".join(self.__format_keybinds(keybindings)),
            capture_output=True,
            encoding="utf-8",
        )

        if walker.returncode != 0:
            return None, Action.CANCEL

        return self.__parse_keybinding(walker.stdout)

    def __format_keybinds(self, keybindings: List[Keybinding]) -> List[str]:
        return [
            f"{keybind.action and keybind.action.value or 'none'}  {keybind.targets and ':'.join([target.raw for target in keybind.targets]) or 'none'}"
            for keybind in [self.select_keybind] + keybindings
        ]

    def __parse_keybinding(self, formatted_string: str) -> Keybinding:
        match = re.compile("(?P<action>.*?) +(?P<targets>.*)").search(formatted_string)

        action = match.group("action").strip()
        targets = match.group("targets").split(":")
        return Keybinding(
            "",
            Action(action) if action != "none" else None,
            [TypeTarget(target_string) for target_string in targets]
            if len(targets) != 1 or targets[0] != self.select_keybind.targets[0].raw
            else None,
        )

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

        walker = run(
            parameters,
            input="\n".join(self._format_targets_from_entry(entry)),
            capture_output=True,
            encoding="utf-8",
        )

        if walker.returncode == 130:
            return None, Action.CANCEL
        elif walker.returncode == 0:
            action = keybindings[0].action
        else:
            action = None

        return (self._extract_targets(walker.stdout)), action

    def __build_parameters_for_keybindings(self, keybindings: List[Keybinding]) -> List[str]:
        params = []
        return params
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
