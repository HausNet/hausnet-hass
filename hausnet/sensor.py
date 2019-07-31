"""Support for HausNet sensors."""
import logging
from asyncio import CancelledError
from typing import Callable, Dict, Optional, Any, Union

from hausnet.builders import DeviceInterface

from homeassistant.components.switch import SwitchDevice
from homeassistant.helpers.entity import Entity
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
    """Set up a sensor. Called multiple times for each platform-based switch
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
    sensor = HausNetSensor(
        config[CONF_DEVICE_FQID],
        interface,
        None if not config[CONF_NAME] else config[CONF_NAME]
    )
    async_add_entities([sensor])
    _LOGGER.debug("Added HausNet sensor: %s", sensor.unique_id)


# noinspection PyAbstractClass
class HausNetSensor(HausNetDevice):
    """Representation of a HausNet Sensor."""

    def __init__(
        self,
        device_id: str,
        device_interface: DeviceInterface,
        name: Optional[str] = None
    ) -> None:
        """Set up the device_interface to the (real) basic switch"""
        super().__init__(device_id, device_interface, name)
        self._state = None

    @property
    def state(self) -> Union[bool, float, int]:
        """Return the current state."""
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement of the sensor."""
        return self._device_interface.device.state.config.unit

    def update_state_from_message(self, message: Dict[str, Any]):
        """On receipt of a state update, the parent class calls here, then
        updates HASS.
        """
        self._state = message['state']
