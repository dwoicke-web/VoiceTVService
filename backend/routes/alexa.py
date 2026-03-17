"""
Alexa Skill endpoint - Receives Alexa voice commands and forwards them
to the existing voice command pipeline for TV control.

Invocation: "Alexa, tell TV Control to turn on all TVs"
            "Alexa, ask TV Control to launch Netflix on upper left"
            "Alexa, tell TV Control to reset antenna"
"""

import asyncio
import logging
from flask import Blueprint
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from flask_ask_sdk.skill_adapter import SkillAdapter

from apis.voice.command_parser import get_command_parser
from apis.sonos import get_sonos_manager
from apis.tv_control.fire_tv import FireTVDevice
from apis.tv_control.roku import RokuDevice
import os

logger = logging.getLogger(__name__)

alexa_bp = Blueprint('alexa', __name__, url_prefix='/api/alexa')

# --- Shared helpers (same as voice.py) ---

FIRE_TVS = {
    'upper_left': {'name': 'Upper Left', 'ip': '192.168.4.80', 'channel': 7},
    'upper_right': {'name': 'Upper Right', 'ip': '192.168.4.78', 'channel': 10},
    'lower_left': {'name': 'Lower Left', 'ip': '192.168.4.93', 'channel': 8},
    'lower_right': {'name': 'Lower Right', 'ip': '192.168.4.108', 'channel': 11},
}


def _get_or_create_event_loop():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def _get_fire_tv(tv_id):
    config = FIRE_TVS.get(tv_id)
    if not config:
        return None
    return FireTVDevice(device_id=tv_id, device_name=config['name'], device_ip=config['ip'])


def _get_roku(tv_id):
    roku_ip = os.environ.get(f'ROKU_{tv_id.upper()}_IP')
    if not roku_ip:
        return None
    config = FIRE_TVS.get(tv_id, {})
    return RokuDevice(
        device_id=f'{tv_id}_roku',
        device_name=f'{config.get("name", tv_id)} Roku',
        device_ip=roku_ip,
        channel=config.get('channel', 0)
    )


def _execute_command(transcript):
    """Parse and execute a voice command, return (speech_text, success)"""
    parser = get_command_parser()
    command = parser.parse_command(transcript)
    intent = command.get('intent')
    loop = _get_or_create_event_loop()

    logger.info(f"Alexa command: '{transcript}' -> intent={intent}")

    if intent == 'control_power':
        result = _exec_power(command, loop)
    elif intent == 'reset_antenna':
        result = _exec_reset(command, loop)
    elif intent == 'tune_channel':
        result = _exec_tune(command, loop)
    elif intent == 'launch_app':
        result = _exec_launch(command, loop)
    elif intent == 'play_content':
        result = _exec_play(command, loop)
    elif intent == 'search':
        result = _exec_search(command, loop)
    elif intent == 'control_volume':
        result = {'status': 'success', 'voice_response': 'Volume control noted'}
    else:
        return f"I didn't understand: {transcript}", False

    voice_response = result.get('voice_response', command.get('voice_response', 'Done'))
    success = result.get('status') == 'success'

    # Also speak on Sonos
    try:
        sonos = get_sonos_manager()
        loop.run_until_complete(sonos.speak(voice_response, volume=35))
    except Exception as e:
        logger.warning(f"Sonos TTS failed: {e}")

    return voice_response, success


def _exec_power(command, loop):
    action = command.get('action', 'on')
    tv_id = command.get('tv_id')

    if tv_id == 'all':
        async def power_all():
            tasks = []
            for tid in FIRE_TVS:
                device = _get_fire_tv(tid)
                if device:
                    coro = device.power_on() if action == 'on' else device.power_off()
                    tasks.append(asyncio.wait_for(coro, timeout=30))
            return await asyncio.gather(*tasks, return_exceptions=True)

        results = loop.run_until_complete(power_all())
        successes = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'success')
        return {
            'status': 'success',
            'voice_response': f"All TVs are now {'on' if action == 'on' else 'off'}"
        }
    elif tv_id:
        device = _get_fire_tv(tv_id)
        if not device:
            return {'status': 'error', 'voice_response': f'TV {tv_id} not found'}
        if action == 'on':
            loop.run_until_complete(device.power_on())
        else:
            loop.run_until_complete(device.power_off())
        return {'status': 'success', 'voice_response': f"{device.device_name} is now {action}"}
    else:
        return {'status': 'error', 'voice_response': 'Which TV? Say all or a specific TV name.'}


def _exec_reset(command, loop):
    tv_id = command.get('tv_id')

    if tv_id == 'all' or not tv_id:
        async def reset_all():
            tasks = []
            for tid, config in FIRE_TVS.items():
                device = _get_fire_tv(tid)
                if device:
                    tasks.append(asyncio.wait_for(device.reset_channel(config['channel']), timeout=30))
            return await asyncio.gather(*tasks, return_exceptions=True)

        loop.run_until_complete(reset_all())
        return {'status': 'success', 'voice_response': 'All TVs reset to antenna'}
    else:
        device = _get_fire_tv(tv_id)
        config = FIRE_TVS.get(tv_id, {})
        if not device:
            return {'status': 'error', 'voice_response': f'TV {tv_id} not found'}
        loop.run_until_complete(device.reset_channel(config.get('channel', 0)))
        return {'status': 'success', 'voice_response': f"{device.device_name} reset to antenna"}


def _exec_tune(command, loop):
    channel = command.get('channel')
    tv_id = command.get('tv_id') or 'upper_left'

    if not channel:
        return {'status': 'error', 'voice_response': 'Which channel should I tune to?'}

    roku = _get_roku(tv_id)
    if roku:
        loop.run_until_complete(roku.tune_channel(channel))
        tv_name = FIRE_TVS.get(tv_id, {}).get('name', tv_id)
        return {'status': 'success', 'voice_response': f"Tuning to {channel} on {tv_name}"}
    else:
        return {'status': 'error', 'voice_response': f"No Roku configured for {tv_id.replace('_', ' ')}"}


def _exec_launch(command, loop):
    service = command.get('service')
    tv_id = command.get('tv_id') or 'upper_left'

    if not service:
        return {'status': 'error', 'voice_response': 'Which app should I launch?'}

    roku = _get_roku(tv_id)
    if roku:
        loop.run_until_complete(roku.launch_app(service))
        tv_name = FIRE_TVS.get(tv_id, {}).get('name', tv_id)
        return {'status': 'success', 'voice_response': f"Launching {service} on {tv_name}"}
    else:
        return {'status': 'error', 'voice_response': f"No Roku configured for {tv_id.replace('_', ' ')}"}


def _exec_play(command, loop):
    content_name = command.get('content_name')
    tv_id = command.get('tv_id') or 'upper_left'
    service = command.get('service')
    mlb_team = command.get('mlb_team')

    if not content_name:
        return {'status': 'error', 'voice_response': 'What should I play?'}

    roku = _get_roku(tv_id)
    if not roku:
        return {'status': 'error', 'voice_response': f'No Roku for {tv_id}'}

    tv_name = FIRE_TVS.get(tv_id, {}).get('name', tv_id)

    # MLB team detected → launch MLB app directly
    if service == 'MLB' or mlb_team:
        loop.run_until_complete(roku.launch_app('MLB'))
        return {'status': 'success', 'voice_response': f"Opening MLB for {mlb_team or content_name} on {tv_name}"}

    # Known streaming service → launch that app
    if service:
        loop.run_until_complete(roku.launch_app(service, content_id=content_name, title=content_name))
        return {'status': 'success', 'voice_response': f"Playing {content_name} on {tv_name}"}

    # Generic content → use Roku search to find it
    loop.run_until_complete(roku.search_content(content_name))
    return {'status': 'success', 'voice_response': f"Searching for {content_name} on {tv_name}"}


def _exec_search(command, loop):
    query = command.get('query')
    if not query:
        return {'status': 'error', 'voice_response': 'What should I search for?'}

    from apis.search import get_search_aggregator
    aggregator = get_search_aggregator()
    results = loop.run_until_complete(aggregator.search(query))
    total = results.get('total', 0)
    top_results = results.get('results', [])[:3]
    titles = [r.get('title', '') for r in top_results]

    voice = f"Found {total} results for {query}."
    if titles:
        voice += f" Top result: {titles[0]}."
    return {'status': 'success', 'voice_response': voice}


# --- Alexa Request Handlers ---

class LaunchRequestHandler(AbstractRequestHandler):
    """Handle skill launch (no specific command)"""

    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        speech = "TV Control is ready. What would you like to do?"
        return (
            handler_input.response_builder
            .speak(speech)
            .ask("You can say things like: turn on all TVs, reset antenna, or launch Netflix.")
            .response
        )


class TVCommandHandler(AbstractRequestHandler):
    """Handle the catch-all TVCommand intent - forwards raw transcript to command parser"""

    def can_handle(self, handler_input):
        return is_intent_name("TVCommandIntent")(handler_input)

    def handle(self, handler_input):
        # Get the raw command from the slot
        slots = handler_input.request_envelope.request.intent.slots
        command_text = ''
        if slots and 'command' in slots and slots['command'].value:
            command_text = slots['command'].value

        logger.info(f"Alexa TVCommandIntent: '{command_text}'")

        if not command_text:
            return (
                handler_input.response_builder
                .speak("I didn't catch that. What would you like me to do?")
                .ask("Try saying: turn on all TVs, or launch Netflix.")
                .response
            )

        try:
            speech, success = _execute_command(command_text)
        except Exception as e:
            logger.error(f"Alexa command execution error: {e}", exc_info=True)
            speech = f"Sorry, something went wrong: {str(e)}"

        return (
            handler_input.response_builder
            .speak(speech)
            .set_should_end_session(True)
            .response
        )


class PowerAllHandler(AbstractRequestHandler):
    """Handle explicit PowerAllIntent"""

    def can_handle(self, handler_input):
        return is_intent_name("PowerAllIntent")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        action = 'on'
        if slots and 'action' in slots and slots['action'].value:
            action = slots['action'].value.lower()
            if action not in ('on', 'off'):
                action = 'on'

        try:
            speech, _ = _execute_command(f"turn {action} all TVs")
        except Exception as e:
            speech = f"Sorry, power command failed: {str(e)}"

        return (
            handler_input.response_builder
            .speak(speech)
            .set_should_end_session(True)
            .response
        )


class ResetAntennaHandler(AbstractRequestHandler):
    """Handle ResetAntennaIntent"""

    def can_handle(self, handler_input):
        return is_intent_name("ResetAntennaIntent")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        tv_name = ''
        if slots and 'tv_name' in slots and slots['tv_name'].value:
            tv_name = slots['tv_name'].value

        command = f"reset antenna{' on ' + tv_name if tv_name else ''}"

        try:
            speech, _ = _execute_command(command)
        except Exception as e:
            speech = f"Sorry, reset failed: {str(e)}"

        return (
            handler_input.response_builder
            .speak(speech)
            .set_should_end_session(True)
            .response
        )


class TuneChannelHandler(AbstractRequestHandler):
    """Handle TuneChannelIntent - tune to a channel on YouTube TV"""

    def can_handle(self, handler_input):
        return is_intent_name("TuneChannelIntent")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        channel_name = ''
        tv_name = ''
        if slots:
            if 'channel_name' in slots and slots['channel_name'].value:
                channel_name = slots['channel_name'].value
            if 'tv_name' in slots and slots['tv_name'].value:
                tv_name = slots['tv_name'].value

        if not channel_name:
            return (
                handler_input.response_builder
                .speak("Which channel should I tune to?")
                .ask("You can say ESPN, CBS, Fox News, CNN, or other channels.")
                .response
            )

        command = f"tune to {channel_name}"
        if tv_name:
            command += f" on {tv_name}"

        try:
            speech, _ = _execute_command(command)
        except Exception as e:
            speech = f"Sorry, couldn't tune to {channel_name}: {str(e)}"

        return (
            handler_input.response_builder
            .speak(speech)
            .set_should_end_session(True)
            .response
        )


class LaunchAppHandler(AbstractRequestHandler):
    """Handle LaunchAppIntent"""

    def can_handle(self, handler_input):
        return is_intent_name("LaunchAppIntent")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        app_name = ''
        tv_name = ''
        if slots:
            if 'app_name' in slots and slots['app_name'].value:
                app_name = slots['app_name'].value
            if 'tv_name' in slots and slots['tv_name'].value:
                tv_name = slots['tv_name'].value

        if not app_name:
            return (
                handler_input.response_builder
                .speak("Which app should I launch?")
                .ask("You can say Netflix, YouTube TV, ESPN, or other apps.")
                .response
            )

        command = f"launch {app_name}"
        if tv_name:
            command += f" on {tv_name}"

        try:
            speech, _ = _execute_command(command)
        except Exception as e:
            speech = f"Sorry, couldn't launch {app_name}: {str(e)}"

        return (
            handler_input.response_builder
            .speak(speech)
            .set_should_end_session(True)
            .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handle AMAZON.HelpIntent"""

    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speech = (
            "You can control your basement TVs. Try saying: "
            "turn on all TVs, "
            "power off all TVs, "
            "reset antenna, "
            "launch Netflix on upper left, "
            "or search for a show."
        )
        return (
            handler_input.response_builder
            .speak(speech)
            .ask("What would you like to do?")
            .response
        )


class CancelStopHandler(AbstractRequestHandler):
    """Handle AMAZON.CancelIntent and AMAZON.StopIntent"""

    def can_handle(self, handler_input):
        return (
            is_intent_name("AMAZON.CancelIntent")(handler_input) or
            is_intent_name("AMAZON.StopIntent")(handler_input)
        )

    def handle(self, handler_input):
        return (
            handler_input.response_builder
            .speak("Goodbye!")
            .set_should_end_session(True)
            .response
        )


class FallbackIntentHandler(AbstractRequestHandler):
    """Handle AMAZON.FallbackIntent"""

    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        speech = "I didn't understand that. Try saying: turn on all TVs, reset antenna, or launch Netflix."
        return (
            handler_input.response_builder
            .speak(speech)
            .ask("What would you like to do?")
            .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handle session ended"""

    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Catch-all exception handler"""

    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error(f"Alexa exception: {exception}", exc_info=True)
        speech = "Sorry, something went wrong. Please try again."
        return (
            handler_input.response_builder
            .speak(speech)
            .ask("What would you like to do?")
            .response
        )


# --- Build Alexa Skill ---

sb = SkillBuilder()

# Add request handlers (order matters - more specific first)
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(PowerAllHandler())
sb.add_request_handler(ResetAntennaHandler())
sb.add_request_handler(TuneChannelHandler())
sb.add_request_handler(LaunchAppHandler())
sb.add_request_handler(TVCommandHandler())  # Catch-all for freeform commands
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelStopHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

# Add exception handler
sb.add_exception_handler(CatchAllExceptionHandler())

# Create skill adapter for Flask
skill_adapter = SkillAdapter(
    skill=sb.create(),
    skill_id=None,  # Set to your Alexa skill ID for production verification
    app=None  # Will be set when blueprint registers
)

# Disable request verification for development (Cloudflare Tunnel doesn't pass Alexa cert validation easily)
# For production, set ALEXA_VERIFY_REQUESTS=true and configure your skill ID
VERIFY_REQUESTS = os.environ.get('ALEXA_VERIFY_REQUESTS', 'false').lower() == 'true'


@alexa_bp.route('/skill', methods=['POST'])
def alexa_skill_endpoint():
    """Main Alexa skill endpoint - receives all Alexa requests"""
    from flask import request as flask_request, make_response
    import json

    logger.info("Alexa skill request received")

    if VERIFY_REQUESTS:
        # Use the SDK's built-in request verification
        return skill_adapter.dispatch_request()
    else:
        # Skip signature verification (for development / Cloudflare Tunnel)
        from ask_sdk_core.serialize import DefaultSerializer
        serializer = DefaultSerializer()
        request_envelope = serializer.deserialize(
            flask_request.data.decode('utf-8'),
            'ask_sdk_model.RequestEnvelope'
        )

        # Invoke the skill
        response_envelope = sb.create().invoke(request_envelope, None)
        response_dict = serializer.serialize(response_envelope)

        flask_response = make_response(json.dumps(response_dict))
        flask_response.headers['Content-Type'] = 'application/json'
        return flask_response
