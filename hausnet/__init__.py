"""Support for HausNet devices."""
import logging

import voluptuous as vol

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.helpers import config_validation as cv, ConfigType
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import HomeAssistantType

DOMAIN = 'hausnet'
INTERFACES = 'interfaces'

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Provided by hausnet.com"
DEFAULT_BRAND = 'HausNet'

CONF_MQTT = 'mqtt'
CONF_SERVER = 'server'
CONF_PORT = 'port'
CONF_DEVICES = 'devices'
CONF_DEVICE_TYPE = 'type'
CONF_DEVICE_ID = 'device_id'

NOTIFICATION_ID = 'hausnet_notification'
NOTIFICATION_TITLE = 'HausNet Component Setup'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_MQTT): vol.Schema({
            vol.Required(CONF_SERVER): cv.string,
            vol.Required(CONF_PORT): cv.port,
        }),
        vol.Required(CONF_DEVICES): vol.Schema({
            vol.Required(str): vol.Schema({
                vol.Required(CONF_DEVICE_TYPE): cv.string,
                vol.Required(CONF_DEVICE_ID): cv.string,
                vol.Required(CONF_DEVICES): vol.Schema({
                    vol.Required(str): vol.Schema({
                        vol.Required(CONF_DEVICE_TYPE): cv.string,
                        vol.Required(CONF_DEVICE_ID): cv.string,
                    })
                })
            }),
        }),
    }),
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistantType, config: ConfigType):
    """Set up a HausNet component."""
    from hausnet.hausnet import HausNet
    hausnet_conf = config[DOMAIN]
    mqtt_conf = hausnet_conf[CONF_MQTT]
    loop = hass.loop
    try:
        hausnet = HausNet(
            loop,
            mqtt_conf[CONF_SERVER],
            mqtt_conf[CONF_PORT],
            hausnet_conf[CONF_DEVICES]
        )
    except Exception as ex:
        _LOGGER.error("Unable to initialize HausNet: %s", str(ex))
        hass.components.persistent_notification.create(
            'Error: {}<br />'
            'You will need to restart hass after fixing.'
            ''.format(ex),
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID)
        return False

    hass.data[DOMAIN] = {INTERFACES: hausnet}
    return True
