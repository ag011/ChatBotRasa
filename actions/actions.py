from typing import Any, Text, Dict, List, Optional
from rasa_sdk import Tracker, FormValidationAction, Action
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
import requests
from datetime import datetime
from dateutil import parser  # To parse natural language dates like "10th July"

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
        return ["source", "destination", "travel_date"]

    def validate_source(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
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

        # Convert date format to dd-MM-yyyy
        try:
            parsed_date = parser.parse(travel_date_raw, fuzzy=True)
            travel_date = parsed_date.strftime("%d-%m-%Y")
        except Exception as e:
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
            else:
                message = "Sorry, no flights found for your search."

        except Exception as e:
            message = f"Failed to fetch flight data: {str(e)}"

        dispatcher.utter_message(text=message)
        return []
