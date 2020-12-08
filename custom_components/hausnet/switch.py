"""Support for HausNet switches."""
import logging
from typing import Callable, Dict, Optional, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.typing import (HomeAssistantType, ConfigType)
from homeassistant.const import CONF_NAME

from hausnet.hausnet import HausNet
from hausnet.builders import DeviceAssembly
from hausnet.states import OnOffState
# noinspection PyUnresolvedReferences
from . import (
    DOMAIN, INTERFACES, CONF_DEVICE_FQID, PLATFORM_SCHEMA, HausNetDevice
)

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
    if CONF_DEVICE_FQID not in config:
        _LOGGER.error("device_fqid not in config: %s", str(config))
        return
    elif config[CONF_DEVICE_FQID] not in hausnet.device_assemblies():
        _LOGGER.error("Device %s no longer exists.", config[CONF_DEVICE_FQID])
        return
    interface = hausnet.device_assemblies()[config[CONF_DEVICE_FQID]]
    switch = HausNetSwitch(
        config[CONF_DEVICE_FQID],
        interface,
        config[CONF_NAME] if CONF_NAME in config else None
    )
    async_add_entities([switch])
    _LOGGER.debug("Added HausNet switch: %s", switch.unique_id)


# noinspection PyAbstractClass
class HausNetSwitch(SwitchEntity, HausNetDevice):
    """Representation of a HausNet Switch."""
    def __init__(
        self,
        device_id: str,
        device_assembly: DeviceAssembly,
        name: Optional[str] = None
    ) -> None:
        """Set up the device_assembly to the (real) basic switch"""
        super().__init__(device_id, device_assembly, name)
        self._is_on = False

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Send the message to turn the switch on"""
        await self._device_assembly.in_queue.put({"state": OnOffState.ON})

    async def async_turn_off(self, **kwargs):
        """Send the message to turn the switch off"""
        await self._device_assembly.in_queue.put({"state": OnOffState.OFF})

    def update_state_from_message(self, message: Dict[str, Any]):
        """Called by parent class when a message arrives"""
        self._is_on = self._device_assembly.device.state.value == OnOffState.ON
