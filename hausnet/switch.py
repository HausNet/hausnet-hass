"""Support for HausNet switches."""
import logging
from asyncio import CancelledError
from typing import Callable, Dict, Optional, Any

from hausnet.builders import DeviceInterface

from homeassistant.components.switch import SwitchDevice
from homeassistant.helpers.typing import HomeAssistantType, ConfigType
from homeassistant.const import CONF_NAME, EVENT_HOMEASSISTANT_START

from hausnet.hausnet import HausNet
from hausnet.states import OnOffState
from . import DOMAIN, INTERFACES, CONF_DEVICE_FQID, HausNetDevice

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
class HausNetSwitch(SwitchDevice, HausNetDevice):
    """Representation of a HausNet Switch."""
    def __init__(
        self,
        device_id: str,
        device_interface: DeviceInterface,
        name: Optional[str] = None
    ) -> None:
        """Set up the device_interface to the (real) basic switch"""
        super().__init__(device_id, device_interface, name)
        self._is_on = False

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Send the message to turn the switch on"""
        await self._device_interface.in_queue.put({"state": OnOffState.ON})

    async def async_turn_off(self, **kwargs):
        """Send the message to turn the switch off"""
        await self._device_interface.in_queue.put({"state": OnOffState.OFF})

    def update_state_from_message(self, message: Dict[str, Any]):
        """Called by parent class when a message arrives"""
        self._is_on = message['state'] == OnOffState.ON
