from __future__ import print_function
import time
import datetime
import dateutil.parser
import pytz
import httplib2
from apiclient.discovery import build
from oauth2client.client import Credentials, OAuth2WebServerFlow

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])


def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return help_response()

def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == 'CalendarNowIntent':
        return calendar_response(time.time())
    elif intent_name == 'CalendarTimeIntent':
        return calendar_time_response(intent)
    elif intent_name == "AMAZON.HelpIntent":
        return help_response()
    else:
        raise ValueError("Invalid intent: %s" % intent_name)


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here

# --------------- Functions that control the skill's behavior ------------------
def calendar_service():
    flow = OAuth2WebServerFlow(
        client_id='<REDACTED>',
        client_secret='<REDACTED>',
        scope='https://www.googleapis.com/auth/calendar.readonly',
        redirect_uri='<REDACTED>',
        approval_prompt='force'
    )

    credentials_json = '<REDACTED>'
    credentials = Credentials.new_from_json(credentials_json)
    if credentials is None or credentials.invalid:
        credentials = run(flow, storage)

    http = httplib2.Http()
    http = credentials.authorize(http)
    return build('calendar', 'v3', http=http)

def calendar_time_response(intent):
    date = intent['slots']['time']['value']
    start_datetime = dateutil.parser.parse(date)
    start_datetime = pytz.timezone('US/Eastern').localize(start_datetime)
    ts = (start_datetime - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds()
    return calendar_response(ts)

def calendar_response(ts, interval=60):
    nearest_thirty_min = int(ts) / 1800 * 1800
    start_datetime = datetime.datetime.utcfromtimestamp(nearest_thirty_min)
    start_date = start_datetime.isoformat('T') + 'Z'
    end_datetime = datetime.datetime.utcfromtimestamp(nearest_thirty_min + interval * 60)
    end_date = end_datetime.isoformat('T') + 'Z'
    print('[CalendarIntent] Checking available calendars between %s and %s' % (start_date, end_date))
    calendars = [
        {'name': 'Brooklyn', 'id': 'betaworks.com_38373732353330332d353934@resource.calendar.google.com'},
        {'name': 'Coney Island', 'id': 'betaworks.com_2d38313332353035353932@resource.calendar.google.com'},
        {'name': 'Manhattan', 'id': 'betaworks.com_3831353934343132363735@resource.calendar.google.com'},
        {'name': 'Queens', 'id': 'betaworks.com_2d3238303434353939323733@resource.calendar.google.com'}
    ]
    available_calendars = []
    service = calendar_service()
    for calendar in calendars:
        events = service.events().list(
            calendarId=calendar['id'],
            timeMin=start_date,
            timeMax=end_date
        ).execute()
        available = True
        for item in events['items']:
            if item['status'] == 'confirmed':
                available = False
                break
        if available:
            available_calendars.append(calendar)
    
    if len(available_calendars) > 2:
        speech_output = ''
        for calendar in available_calendars[:-1]:
            speech_output += '%s, ' % calendar['name']
        speech_output += 'and %s are all available' % available_calendars[-1]['name']
    elif len(available_calendars) == 2:
        speech_output = '%s and %s are both available' % (available_calendars[0]['name'], available_calendars[1]['name'])
    elif len(available_calendars) == 1:
        speech_output = '%s is available' % (available_calendars[0]['name'])
    elif interval == 60:
        return calendar_response(ts, interval=30)
    else:
        speech_output = 'Oh shucks. Looks like there are no rooms availalbe.'

    if interval != 60:
        speech_output += ' until %s' % local_time_from_datetime(end_datetime)
    else:
        speech_output += ' at %s' % local_time_from_datetime(start_datetime)
    
    return build_response(
        {},
        build_speechlet_response(speech_output)
    )

def local_time_from_datetime(dt):
    utc_dt = pytz.utc.localize(dt)
    local_dt = utc_dt.astimezone(pytz.timezone('US/Eastern'))
    return local_dt.strftime('%I:%M %p')

def help_response():
    return build_response(
        {},
        build_speechlet_response(
            "You can ask which conference room is available now or at a specific time."
        )
    )


# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(output, card_title=None, card_content=None,
                             reprompt='', should_end_session=True):
    response =  {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt
            }
        },
        'shouldEndSession': should_end_session
    }

    if card_title and card_content:
        response['card'] = {
            'type': 'Simple',
            'title': card_title,
            'content': card_content
        }

    return response

def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }

