import json
import re
import os

import streamlit as st
from openai import OpenAI
from enum import Enum
from typing import Union
from notion_client import Client
from streamlit.delta_generator import DeltaGenerator
from dotenv import load_dotenv

from gcal import setup, add_to_calendar
from utils import get_local_date
from oauth import block_on_oauth

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
notion = Client(auth=os.getenv("NOTION_API_KEY"))

DATE_REGEX = r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$"


class Param:
    def __init__(self, content: str, description: str, default: str | None = None, regex: str | None = None):
        self.content = content
        self.description = description
        self.default = default
        self.regex = regex


class Capability(Enum):
    ADD_TO_GCAL = "addToGcal"
    ADD_TO_JOURNAL = "addToJournal"
    ADD_TO_GOOD_MOMENTS_JOURNAL = "addToGoodMomentsJournal"


capabilities: dict[Capability, str] = {
    Capability.ADD_TO_GCAL.value: "add to google calendar",
    Capability.ADD_TO_JOURNAL.value: "add to journal",
    Capability.ADD_TO_GOOD_MOMENTS_JOURNAL.value: "add to good moments journal"
}


class AddToGoodMomentsJournalParams:
    def __init__(self):
        self.entry = Param(
            content="", description="The content of the good moment.")
        self.date = Param(
            content="", description="The date that the good moment occurred.", default=get_local_date(), regex=DATE_REGEX)


class AddToJournalParams:
    def __init__(self):
        self.entry = Param(
            content="", description="The content of the journal entry.")
        self.date = Param(
            content="", description="The date that the journal entry occurred.", default=get_local_date())


class AddToGcalParams:
    def __init__(self):
        self.name = Param(
            content="", description="The name of the event.")
        self.startDatetime = Param(
            content="", description="The start datetime of the event. Please format as ISO 8601 with UTC-5:00 timezone unless otherwise specified.")
        self.endDatetime = Param(
            content="", description="The end datetime of the event. Please format as ISO 8601 with UTC-5:00 timezone unless otherwise specified. Default to 30 minutes after the start time.")


ParamType = Union[AddToGoodMomentsJournalParams, AddToJournalParams]


def get_specific_params_object(task: Capability) -> ParamType:
    match task:
        case "addToGcal":
            return AddToGcalParams()
        case "addToJournal":
            return AddToJournalParams()
        case "addToGoodMomentsJournal":
            return AddToGoodMomentsJournalParams()


def get_capabilities():
    output_str = "{ "

    for capability in capabilities:
        output_str += capability + ": '" + capabilities[capability] + "', "

    output_str += " }"

    return output_str


@st.cache_data
def identify_task(text: str):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content":
                "You are given a list of capabilities and an input string from the user. This list of capabilities is formatted as { capability: 'description' }. Your goal is to use the input string to identify what capability the user is asking for. The output should be only one word, the capability that the user is asking for. For example, if the list of capabilities is { addToGcal: 'add to google calendar', addToJournal: 'add to journal' } and the input string is 'add to my calendar', the output should be 'addToGcal'.",
            },
            {
                "role": "system",
                "content":
                f'The list of capabilities is {get_capabilities()}.',
            },
            {"role": "user", "content": text},
        ]
    )

    response = completion.choices[0].message.content

    for capability in capabilities:
        if capability in response:
            return capability

    return "none"


def get_param_descriptions_as_string(inputParamObject):
    output_str = "{ "

    for paramKey in vars(inputParamObject):
        paramObject: Param = getattr(inputParamObject, paramKey)
        output_str += paramKey + ": '" + paramObject.description + "', "

    output_str += " }"

    return output_str


@st.cache_data
def pull_params_as_json_string_from_text(text: str, _inputParamObject):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content":
                f"You are given a list of parameters and descriptions as well as an input string from the user. Please fill the parameters and return filled parameters as a JSON. For example, if the parameters are {{ text: 'the text to add to the journal', date: 'the date to add to the journal' }} and the input string is 'add to good moment on Nov 12 2023 that I had a good time with my friends', the output should be {{ text: 'good time with my friends', date: '2023-11-12' }}. If the content of a field is unclear, please leave it out. For instance, if date is not specified by the month and day, please exclude the date parameter. Note that today refers to {get_local_date()}.",
            },
            {
                "role": "system",
                "content":
                f'The list of parameters is {get_param_descriptions_as_string(_inputParamObject)}.',
            },
            {"role": "user", "content": text},
        ]
    )

    response = completion.choices[0].message.content

    return response


@st.cache_data
def get_params_of_task(text: str, _task: Capability, _expander: DeltaGenerator):
    task_params = get_specific_params_object(_task)

    json_string = pull_params_as_json_string_from_text(
        text, task_params)

    if json_string is not None:
        json_object = json.loads(json_string)
        # NOTE: writing the json object
        _expander.write("Param JSON object:")
        _expander.write(json_object)

        for paramKey in vars(task_params):
            paramObject: Param = getattr(
                task_params, paramKey)
            try:
                content = json_object[paramKey]
                if paramObject.regex is not None:
                    if not re.match(paramObject.regex, content):
                        raise Exception
                paramObject.content = content
            except:
                if paramObject.default is None:
                    _expander.write(
                        f"Tried to use default value for {paramKey} but none existed.")
                    return None
                _expander.write(
                    f"Set {paramKey} to default value: {paramObject.default}")
                paramObject.content = paramObject.default
    else:
        return None

    return task_params


@st.cache_data
def execute_task(text: str, _task: Capability, _params: ParamType):
    # LATER: account for non-completed params and request the user
    match _task:
        case Capability.ADD_TO_GCAL.value:
            gcal_params: AddToGcalParams = _params
            input_event = {
                'summary': gcal_params.name.content,
                'start': {
                    'dateTime': gcal_params.startDatetime.content,
                },
                'end': {
                    'dateTime': gcal_params.endDatetime.content,
                },
            }
            service = setup()
            if service is not None:
                event = add_to_calendar(service, input_event)
                st.write(
                    f"Added to GCal: {gcal_params.startDatetime.content} - [{gcal_params.name.content}]({event.get('htmlLink')})")

        case Capability.ADD_TO_JOURNAL.value:
            journal_params: AddToJournalParams = _params
            notion.pages.create(**{
                "parent": {
                    "database_id": os.getenv("NOTION_JOURNAL_DATABASE_ID")
                },
                "properties": {
                    "Date": {
                        "type": "date",
                        "date": {
                            "start": journal_params.date.content
                        }
                    },
                    "Name": {
                        "title": [
                            {
                                "text": {
                                    "content": journal_params.entry.content
                                }
                            }
                        ]
                    },
                }
            })
            st.write(
                f"Added to Journal: {journal_params.date.content} - {journal_params.entry.content}")
        case Capability.ADD_TO_GOOD_MOMENTS_JOURNAL.value:
            good_moments_params: AddToGoodMomentsJournalParams = _params
            notion.pages.create(**{
                "parent": {
                    "database_id": os.getenv("NOTION_GOOD_MOMENTS_DATABASE_ID")
                },
                "properties": {
                    "Date": {
                        "type": "date",
                        "date": {
                            "start": good_moments_params.date.content
                        }
                    },
                    "Name": {
                        "title": [
                            {
                                "text": {
                                    "content": good_moments_params.entry.content
                                }
                            }
                        ]
                    },
                }
            })
            st.write(
                f"Added to Good Moments: {good_moments_params.date.content} - {good_moments_params.entry.content}")


def main():
    st.title("Misc task completer")
    if block_on_oauth():
        return

    input_text = st.text_input("Enter task")

    if len(input_text) > 0:
        expander = st.expander("Show process")
        task = identify_task(input_text)
        expander.write("Identified task: " + str(task))
        if (task != "none"):
            params = get_params_of_task(input_text, task, expander)
            if params is not None:
                execute_task(input_text, task, params)
                return
            else:
                st.error("Necessary params were not identified from the string")
                return
        else:
            st.error("Task was not identified from the string")
            return


main()
