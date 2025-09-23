import datetime
import os
import operator
from queue import Queue
from typing import Annotated, Final, Optional, TypedDict
import uuid

from pydantic import BaseModel, Field

import serpapi
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from langchain_core.tools import tool
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph


SENDING_QUESTION_SYSTEM_PROMPT: Final[str] = f"""
You are a smart travel agency. Use the tools to look up information.
You are allowed to make multiple calls (either together or in sequence).
Only look up information when you are sure of what you want.
The current year is {datetime.datetime.now().year}.
If you need to look up some information before asking a follow up question, you are allowed to do that!
I want to have in your output links to hotels websites and flights websites (if possible).
I want to have as well the logo of the hotel and the logo of the airline company (if possible).
In your output always include the price of the flight and the price of the hotel and the currency as well (if possible).
for example for hotels-
Rate: $581 per night
Total: $3,488
"""

SENDING_EMAIL_SYSTEM_PROMPT: Final[str] = """
Your task is to convert structured markdown-like text into a valid HTML email body.
- Do not include a ```html preamble in your response.
- The output should be in proper HTML format, ready to be used as the body of an email.

Here is an example:
<example>
Input:
I want to travel to New York from Madrid from October 1-7. Find me flights and 4-star hotels.

Expected Output:
<!DOCTYPE html>
<html>
<head>
    <title>Flight and Hotel Options</title>
</head>
<body>
    <h2>Flights from Madrid to New York</h2>
    <ol>
        <li>
            <strong>American Airlines</strong><br>
            <strong>Departure:</strong> Adolfo Suárez Madrid–Barajas Airport (MAD) at 10:25 AM<br>
            <strong>Arrival:</strong> John F. Kennedy International Airport (JFK) at 12:25 PM<br>
            <strong>Duration:</strong> 8 hours<br>
            <strong>Aircraft:</strong> Boeing 777<br>
            <strong>Class:</strong> Economy<br>
            <strong>Price:</strong> $702<br>
            <img src="https://www.gstatic.com/flights/airline_logos/70px/AA.png" alt="American Airlines"><br>
            <a href="https://www.google.com/flights">Book on Google Flights</a>
        </li>
        <li>
            <strong>Iberia</strong><br>
            <strong>Departure:</strong> Adolfo Suárez Madrid–Barajas Airport (MAD) at 12:25 PM<br>
            <strong>Arrival:</strong> John F. Kennedy International Airport (JFK) at 2:40 PM<br>
            <strong>Duration:</strong> 8 hours 15 minutes<br>
            <strong>Aircraft:</strong> Airbus A330<br>
            <strong>Class:</strong> Economy<br>
            <strong>Price:</strong> $702<br>
            <img src="https://www.gstatic.com/flights/airline_logos/70px/IB.png" alt="Iberia"><br>
            <a href="https://www.google.com/flights">Book on Google Flights</a>
        </li>
        <li>
            <strong>Delta Airlines</strong><br>
            <strong>Departure:</strong> Adolfo Suárez Madrid–Barajas Airport (MAD) at 10:00 AM<br>
            <strong>Arrival:</strong> John F. Kennedy International Airport (JFK) at 12:30 PM<br>
            <strong>Duration:</strong> 8 hours 30 minutes<br>
            <strong>Aircraft:</strong> Boeing 767<br>
            <strong>Class:</strong> Economy<br>
            <strong>Price:</strong> $738<br>
            <img src="https://www.gstatic.com/flights/airline_logos/70px/DL.png" alt="Delta Airlines"><br>
            <a href="https://www.google.com/flights">Book on Google Flights</a>
        </li>
    </ol>
    <h2>4-Star Hotels in New York</h2>
    <ol>
        <li>
            <strong>NobleDen Hotel</strong><br>
            <strong>Description:</strong> Modern, polished hotel offering sleek rooms, some with city-view balconies, plus free Wi-Fi.<br>
            <strong>Location:</strong> Near Washington Square Park, Grand St, and JFK Airport.<br>
            <strong>Rate per Night:</strong> $537<br>
            <strong>Total Rate:</strong> $3,223<br>
            <strong>Rating:</strong> 4.8/5 (656 reviews)<br>
            <strong>Amenities:</strong> Free Wi-Fi, Parking, Air conditioning, Restaurant, Accessible, Business centre, Child-friendly, Smoke-free property<br>
            <img src="https://lh5.googleusercontent.com/p/AF1QipNDUrPJwBhc9ysDhc8LA822H1ZzapAVa-WDJ2d6=s287-w287-h192-n-k-no-v1" alt="NobleDen Hotel"><br>
            <a href="http://www.nobleden.com/">Visit Website</a>
        </li>
        <!-- More hotel entries here -->
    </ol>
</body>
</html>

</example>
"""


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


class FlightsInput(BaseModel):
    departure_airport: Optional[str] = Field(description='Departure airport code (IATA)')
    arrival_airport: Optional[str] = Field(description='Arrival airport code (IATA)')
    outbound_date: Optional[str] = Field(description='Parameter defines the outbound date. The format is YYYY-MM-DD. e.g. 2024-06-22')
    return_date: Optional[str] = Field(description='Parameter defines the return date. The format is YYYY-MM-DD. e.g. 2024-06-28')
    adults: Optional[int] = Field(1, description='Parameter defines the number of adults. Default to 1.')
    children: Optional[int] = Field(0, description='Parameter defines the number of children. Default to 0.')
    infants_in_seat: Optional[int] = Field(0, description='Parameter defines the number of infants in seat. Default to 0.')
    infants_on_lap: Optional[int] = Field(0, description='Parameter defines the number of infants on lap. Default to 0.')


class FlightsInputSchema(BaseModel):
    params: FlightsInput
    

class HotelsInput(BaseModel):
    q: str = Field(description='Location of the hotel')
    check_in_date: str = Field(description='Check-in date. The format is YYYY-MM-DD. e.g. 2024-06-22')
    check_out_date: str = Field(description='Check-out date. The format is YYYY-MM-DD. e.g. 2024-06-28')
    sort_by: Optional[str] = Field(8, description='Parameter is used for sorting the results. Default is sort by highest rating')
    adults: Optional[int] = Field(1, description='Number of adults. Default to 1.')
    children: Optional[int] = Field(0, description='Number of children. Default to 0.')
    rooms: Optional[int] = Field(1, description='Number of rooms. Default to 1.')
    hotel_class: Optional[str] = Field(
        None, description='Parameter defines to include only certain hotel class in the results. for example- 2,3,4')


class HotelsInputSchema(BaseModel):
    params: HotelsInput


@tool(args_schema=FlightsInputSchema)
def search_flights(params: FlightsInput):
    '''
    Find flights using the Google Flights engine.

    Returns:
        dict: Flight search results.
    '''

    params = {
        'api_key': os.environ.get('SERPAPI_KEY'),
        'engine': 'google_flights',
        'hl': 'en',
        'gl': 'us',
        'departure_id': params.departure_airport,
        'arrival_id': params.arrival_airport,
        'outbound_date': params.outbound_date,
        'return_date': params.return_date,
        'currency': 'USD',
        'adults': params.adults,
        'infants_in_seat': params.infants_in_seat,
        'stops': '1',
        'infants_on_lap': params.infants_on_lap,
        'children': params.children
    }

    try:
        search = serpapi.search(params)
        results = search.data['best_flights']
    except Exception as e:
        results = str(e)
    return results


@tool(args_schema=HotelsInputSchema)
def search_hotels(params: HotelsInput):
    '''
    Find hotels using the Google Hotels engine.

    Returns:
        dict: Hotel search results.
    '''

    params = {
        'api_key': os.environ.get("SERPAPI_KEY"),
        'engine': 'google_hotels',
        'hl': 'en',
        'gl': 'us',
        'q': params.q,
        'check_in_date': params.check_in_date,
        'check_out_date': params.check_out_date,
        'currency': 'USD',
        'adults': params.adults,
        'children': params.children,
        'rooms': params.rooms,
        'sort_by': params.sort_by,
        'hotel_class': params.hotel_class
    }

    search = serpapi.search(params)
    results = search.data
    return results['properties'][:5]


class JourneyDiscoveryAgent:
    def __init__(self, queue: Queue):
        self._tools = {tool.name: tool for tool in [search_flights, search_hotels]}
        self._queue = queue
        self._state_graph = (
            StateGraph(AgentState)
            .add_node("handle_sending_question", self._handle_sending_question)
            .add_node("_handle_calling_tools", self._handle_calling_tools)
            .add_node("handle_sending_email", self._handle_sending_email)
            .set_entry_point("handle_sending_question")
            .add_conditional_edges(
                "handle_sending_question",
                self._if_sending_email,
                {
                    "calling_tool": "_handle_calling_tools",
                    "sending_email": "handle_sending_email",
                },
            )
            .add_edge("_handle_calling_tools", "handle_sending_question")
            .add_edge("handle_sending_email", END)
            .compile(
                checkpointer=MemorySaver(),
                interrupt_before=["handle_sending_email"],
            )
        )
        self._model = AzureChatOpenAI(
            azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
            model=os.environ["AZURE_OPENAI_MODEL"],
            temperature=0,
            streaming=False,
        )
        
    def entrypoint(self, input: str):
        try:
            thread_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}
            response = self._state_graph.invoke(
                {"messages": [HumanMessage(content=input)]},
                config=config,
            )
            response = {"output": response["messages"][-1].content}
        except Exception as e:
            print(f"Error during agent execution: {e}")
            response = {"error": str(e)}
            raise e

        self._queue.put({
            "type": "response",
            "data": response,
        })
        
    def _handle_sending_question(self, state: AgentState):
        response = self._model.bind_tools(self._tools.values()).invoke(
            [SystemMessage(content=SENDING_QUESTION_SYSTEM_PROMPT)] +
            state["messages"]
        )
        return {"messages": [response]}
    
    def _handle_calling_tools(self, state: AgentState):
        results = []
        for tool in state["messages"][-1].tool_calls:
            result = self._tools[tool["name"]].invoke(tool["args"])
            results.append(
                ToolMessage(
                    tool_call_id=tool["id"],
                    name=tool["name"],
                    content=str(result),
                )
            )
        return {"messages": results}
    
    def _handle_sending_email(self, state: AgentState):
        response = self._model.invoke([
            SystemMessage(content=SENDING_EMAIL_SYSTEM_PROMPT),
            HumanMessage(content=state['messages'][-1].content),
        ])

        SendGridAPIClient(os.environ.get('SENDGRID_API_KEY')).send(
            Mail(
                from_email=os.environ['FROM_EMAIL'],
                to_emails=os.environ['TO_EMAIL'],
                subject=os.environ['EMAIL_SUBJECT'],
                html_content=response.content,
            )
        )
    

    @staticmethod
    def _if_sending_email(state: AgentState) -> str:
        result = state["messages"][-1]
        if len(result.tool_calls) == 0:
            return "sending_email"
        return "calling_tool"