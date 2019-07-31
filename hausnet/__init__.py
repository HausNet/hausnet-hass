"""Support for HausNet devices."""
import logging
from typing import Optional, Any, Dict

import voluptuous as vol
from hausnet.builders import DeviceInterface

from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.helpers import config_validation as cv, ConfigType
from homeassistant.helpers.entity import Entity
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
CONF_DEVICE_FQID = 'device_fqid'

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


class HausNetDevice(Entity):
    """Shared attributes of all device types"""

    def __init__(
        self,
        device_id: str,
        device_interface: DeviceInterface,
        name: Optional[str] = None
    ):
        self._unique_id = device_id
        self._name = name
        self._device_interface = device_interface
        self._available = True
        self._read_task = None

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def should_poll(self) -> bool:
        """Return False, entity pushes its state to HA."""
        return False

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def available(self) -> bool:
        """Return true if the switch is available."""
        return self._available

    async def async_added_to_hass(self):
        """Create a task to kick off reading device updates, _after_ HASS
        has started
        """
        self.hass.bus.async_listen(
            EVENT_HOMEASSISTANT_START,
            self.start_reading_device_data()
        )

    async def async_will_remove_from_hass(self) -> None:
        """Stop the async data read task"""
        if not self._read_task:
            return
        self._read_task.stop()
        self._read_task = None

    async def start_reading_device_data(self):
        """Creates an async task to read data from the device's output queue,"""
        self._read_task = self.hass.async_create_task(self.read_device_data())

    async def read_device_data(self):
        """Loop for ever retrieving messages from the device queue"""
        while True:
            # noinspection PyBroadException
            try:
                message = await self._device_interface.out_queue.get()
                self._device_interface.out_queue.task_done()
                _LOGGER.debug(
                    "Got message for device %s: %s",
                    self.unique_id,
                    str(message)
                )
                self.update_state_from_message(message)
                self.async_schedule_update_ha_state()
            except (KeyboardInterrupt, CancelledError):
                pass
            except Exception:
                _LOGGER.exception(
                    "Exception while reading from device %s.",
                    self.unique_id
                )

    def update_state_from_message(self, message: Dict[str, Any]):
        """Called by the async read function when a new message arrives.
        Every derived class should handle this in its own way.
        """
        assert "Must be overridden!"

"""Later ?
    @property
    def device_info(self):
        #Return a device description for device registry.
        if (self.unique_id is None or
                self._device.uniqueid.count(':') != 7):
            return None

        serial = self._device.uniqueid.split('-', 1)[0]
        bridgeid = self.gateway.api.config.bridgeid

        return {
            'connections': {(CONNECTION_ZIGBEE, serial)},
            'identifiers': {(DECONZ_DOMAIN, serial)},
            'manufacturer': self._device.manufacturer,
            'model': self._device.modelid,
            'name': self._device.name,
            'sw_version': self._device.swversion,
            'via_device': (DECONZ_DOMAIN, bridgeid),
        }
"""
