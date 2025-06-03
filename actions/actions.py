from typing import Any, Text, Dict, List, Optional
from rasa_sdk import Tracker, FormValidationAction, Action
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
import requests


class ValidateFlightForm(FormValidationAction):
    def name(self) -> Text:
        return "flight_form"

    async def required_slots(
        self,
        slots_mapped_in_domain: List[Text],
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Optional[List[Text]]:
        # Ask slots in order
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
        travel_date = tracker.get_slot("travel_date")

        if not source or not destination or not travel_date:
            dispatcher.utter_message(text="Please provide all the flight details before searching.")
            return []

        payload = {
            "source": source,
            "destination": destination,
            "travelDate": travel_date
        }

        try:
            response = requests.post("http://localhost:8080/chatbot/flight_search", json=payload)
            flights = response.json()

            if flights:
                message = "Here are some available flights:\n"
                for flight in flights:
                    message += (
                        f"{flight['airline']} {flight['flightNumber']} from {flight['source']} to {flight['destination']} "
                        f"on {flight['travelDate']} departs at {flight['departureTime']} and arrives at {flight['arrivalTime']}. "
                        f"Price: ₹{flight['price']}\n"
                    )
            else:
                message = "Sorry, no flights found for your search."

        except Exception as e:
            message = f"Failed to fetch flight data: {str(e)}"

        dispatcher.utter_message(text=message)
        return []
