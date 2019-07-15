"""Support for HausNet switches."""
import logging
from asyncio import CancelledError
from typing import Callable, Dict, Optional

from hausnet.builders import DeviceInterface

from homeassistant.components.switch import SwitchDevice
from homeassistant.helpers.typing import HomeAssistantType, ConfigType
from homeassistant.const import CONF_NAME, EVENT_HOMEASSISTANT_START

from hausnet.hausnet import HausNet
from hausnet.states import OnOffState
from . import DOMAIN, INTERFACES

# Fully-qualified device ID handle, containing node and device ID's
CONF_DEVICE_FQID = 'device_fqid'

_LOGGER = logging.getLogger(__name__)


# noinspection PyUnusedLocal
async def async_setup_platform(
        hass: HomeAssistantType,
        config: ConfigType,
        async_add_entities: Callable,
        discovery_info: Dict
) -> None:
    """Set up a switch. Called multiple times for each platform-based switch
    in configuration.

    :param hass:               HA internals
    :param config:             Configuration from file
    :param async_add_entities: Callee to add entities
    :param discovery_info:     Unused
    """
    assert DOMAIN in hass.data, "HausNet domain must be defined"
    devices = []
    hausnet: HausNet = hass.data[DOMAIN][INTERFACES]
    interface = hausnet.device_interfaces[config[CONF_DEVICE_FQID]]
    switch = HausNetSwitch(
        config[CONF_DEVICE_FQID],
        interface,
        None if not config[CONF_NAME] else config[CONF_NAME]
    )
    async_add_entities([switch])
    _LOGGER.debug("Added HausNet switch: %s", switch.unique_id)


# noinspection PyAbstractClass
class HausNetSwitch(SwitchDevice):
    """Representation of a HausNet Switch."""
    def __init__(
        self,
        device_id: str,
        device_interface: DeviceInterface,
        name: Optional[str] = None
    ) -> None:
        """Set up the device_interface to the (real) basic switch"""
        super().__init__()
        self._unique_id = device_id
        self._name = name
        self._device_interface = device_interface
        self._is_on = False
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
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on

    @property
    def available(self) -> bool:
        """Return true if the switch is available."""
        return self._available

    async def async_turn_on(self, **kwargs):
        """Send the message to turn the switch on"""
        await self._device_interface.in_queue.put({"state": OnOffState.ON})

    async def async_turn_off(self, **kwargs):
        """Send the message to turn the switch off"""
        await self._device_interface.in_queue.put({"state": OnOffState.OFF})

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
                    "Got message for switch %s: %s",
                    self.unique_id,
                    str(message)
                )
                self._is_on = message['state'] == OnOffState.ON
                self.async_schedule_update_ha_state()
            except (KeyboardInterrupt, CancelledError):
                pass
            except Exception:
                _LOGGER.exception(
                    "Exception while reading from device %s.",
                    self.unique_id
                )


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
