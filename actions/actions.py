from typing import Any, Text, Dict, List, Optional
from rasa_sdk import Tracker, FormValidationAction, Action
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet
import requests
from datetime import datetime
from dateutil import parser


class ValidateFlightForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_flight_form"

    async def required_slots(
        self,
        slots_mapped_in_domain: List[Text],
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Optional[List[Text]]:
        # Ask for confirm_flight_details only after others are filled
        if not tracker.slots.get("source"):
            return ["source"]
        if not tracker.slots.get("destination"):
            return ["destination"]
        if not tracker.slots.get("travel_date"):
            return ["travel_date"]
        if not tracker.slots.get("confirm_flight_details"):
            return ["confirm_flight_details"]
        return ["source", "destination", "travel_date", "confirm_flight_details"]

    def _extract_corrected_city(self, text: str, entities: List[Dict], entity_type: str) -> Optional[str]:
        city_values = [e["value"] for e in entities if e["entity"] == entity_type]
        text = text.lower()
        if "not" in text and len(city_values) == 2:
            return city_values[0]
        elif city_values:
            return city_values[-1]
        return None

    def validate_source(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        latest_intent = tracker.latest_message.get("intent", {}).get("name")
        entities = tracker.latest_message.get("entities", [])
        text = tracker.latest_message.get("text", "")

        if latest_intent == "change_source" or "not" in text.lower():
            corrected = self._extract_corrected_city(text, entities, "source")
            if corrected:
                dispatcher.utter_message(text=f"Updated your departure city to {corrected}.")
                return {"source": corrected}
            dispatcher.utter_message(text="Please specify the new departure city.")
            return {"source": None}

        if value and len(value) > 1:
            return {"source": value}

        dispatcher.utter_message(text="Please enter a valid departure city.")
        return {"source": None}

    def validate_destination(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        latest_intent = tracker.latest_message.get("intent", {}).get("name")
        entities = tracker.latest_message.get("entities", [])
        text = tracker.latest_message.get("text", "")

        if latest_intent == "change_destination" or "not" in text.lower():
            corrected = self._extract_corrected_city(text, entities, "destination")
            if corrected:
                dispatcher.utter_message(text=f"Updated your destination to {corrected}.")
                return {"destination": corrected}
            dispatcher.utter_message(text="Please specify the new destination city.")
            return {"destination": None}

        if value and len(value) > 1:
            return {"destination": value}

        dispatcher.utter_message(text="Please enter a valid destination city.")
        return {"destination": None}

    def validate_travel_date(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if value and len(value) > 3:
            return {"travel_date": value}
        dispatcher.utter_message(text="Please enter a valid travel date.")
        return {"travel_date": None}

    def validate_confirm_flight_details(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> Dict[Text, Any]:
        intent = tracker.latest_message.get("intent", {}).get("name")
        value_cleaned = value.strip().lower()
        if intent == "affirm" or value_cleaned in ["yes", "yeah", "yup", "sure"]:
            return {"confirm_flight_details": "yes"}
        elif intent == "deny" or value_cleaned in ["no", "nope", "nah"]:
            dispatcher.utter_message(text="Okay, let's update your travel details.")
            return {
                "source": None,
                "destination": None,
                "travel_date": None,
                "confirm_flight_details": None
            }
        else:
            dispatcher.utter_message(text="Please confirm with 'yes' or 'no'.")
            return {"confirm_flight_details": None}


class ActionSearchFlight(Action):
    def name(self) -> Text:
        return "action_search_flight"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[Text, Any]]:

        source = tracker.get_slot("source")
        destination = tracker.get_slot("destination")
        travel_date_raw = tracker.get_slot("travel_date")

        if not source or not destination or not travel_date_raw:
            dispatcher.utter_message(text="Please provide all the flight details before searching.")
            return []

        try:
            parsed_date = parser.parse(travel_date_raw, fuzzy=True)
            travel_date = parsed_date.strftime("%d-%m-%Y")
        except Exception:
            dispatcher.utter_message(text="Sorry, I couldn't understand the travel date. Please rephrase it.")
            return []

        payload = {
            "source": source,
            "destination": destination,
            "travelDate": travel_date
        }

        try:
            response = requests.post("http://localhost:8080/chatbot/flight_search", json=payload)
            res = response.json()

            message = res.get("message", "Here are the results:")
            flights = res.get("flights", [])

            if flights:
                message += f"\n\nFrom {source} to {destination} on {travel_date}:\n"
                for flight in flights:
                    message += (
                        f"- {flight['airline']} {flight['flightNumber']}: "
                        f"Departs at {flight['departureTime']}, Arrives at {flight['arrivalTime']}, "
                        f"Price ₹{flight['price']}\n"
                    )
                message += "\nWould you like to search for more flights or try something else?"
            else:
                message = "Sorry, no flights found for your search."

        except Exception as e:
            message = f"Failed to fetch flight data: {str(e)}"

        dispatcher.utter_message(text=message)
        return []


class ActionResetFlightForm(Action):
    def name(self) -> Text:
        return "action_reset_flight_form"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="Sure, let's start your flight search again.")
        return [
            SlotSet("source", None),
            SlotSet("destination", None),
            SlotSet("travel_date", None),
            SlotSet("confirm_flight_details", None)
        ]
    
# In actions.py
class ActionTalkToAgent(Action):
    def name(self) -> Text:
        return "action_talk_to_agent"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        user_message = tracker.latest_message.get("text")

        payload = {
            "userMessage": user_message,
            "intent": tracker.latest_message.get("intent", {}).get("name")
        }

        try:
            response = requests.post(
                "http://localhost:8080/chatbot/escalate_to_agent",  # Replace with your host/port if needed
                json=payload
            )

            if response.status_code == 200:
                message = response.json().get("responseText", "You are being connected to an agent.")
            else:
                message = "There was an issue connecting to the agent. Please try again later."

        except Exception as e:
            message = f"Something went wrong: {str(e)}"

        dispatcher.utter_message(text=message)
        return []