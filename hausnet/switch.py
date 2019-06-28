"""Support for HausNet switches."""
import logging
from typing import Callable, Dict, Optional

from hausnet.builders import DeviceInterface

from homeassistant.components.switch import SwitchDevice
from homeassistant.helpers.typing import HomeAssistantType, ConfigType
from homeassistant.const import STATE_ON, STATE_OFF, CONF_NAME

from hausnet.hausnet import HausNet
from hausnet.devices import BasicSwitch
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
    """Set up the switches. Depends on each switch being defined in
    configuration, and this function being called for each switch.

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
    _LOGGER.debug("Added HausNet switch: %s", str(config[CONF_DEVICE_FQID]))


# noinspection PyAbstractClass
class HausNetSwitch(SwitchDevice):
    """Representation of a HausNet Switch."""
    def __init__(
        self,
        device_id: str,
        interface: DeviceInterface,
        name: Optional[str]
    ) -> None:
        """Set up the interface to the (real) basic switch"""
        super().__init__()
        self._unique_id = device_id
        self._name = name
        self._interface = interface
        self._is_on = False
        self._available = True

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
        """Return a unique ID.

        TODO: Make it so fully qualified device ID is returned.
        """
        return self.name

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        _LOGGER.debug(
            "Hausnet switch 'is_on' called: %s",
            "ON" if self._is_on else "OFF"
        )
        return self._is_on

    @property
    def available(self) -> bool:
        """Return true if the switch is available."""
        return self._available

    # noinspection PyRedeclaration
    @property
    def should_poll(self) -> bool:
        """No polling needed for a switch."""
        return False

    async def async_turn_on(self, **kwargs):
        """Send the message to turn the switch on"""
        await self._interface.in_queue.put({"state": OnOffState.ON})
        self.hass.states.async_set(self.entity_id, STATE_ON)
        self._is_on = True
        _LOGGER.debug("Turned Hausnet switch '%s' ON", self._name)

    async def async_turn_off(self, **kwargs):
        """Send the message to turn the switch off"""
        await self._interface.in_queue.put({"state": OnOffState.OFF})
        self.hass.states.async_set(self.entity_id, STATE_OFF)
        self._is_on = False
        _LOGGER.debug("Turned Hausnet switch '%s' OFF", self._name)


"""Later ?
    async def async_update(self):
        switch_state = self.hass.states.get(self._entity_id)
        _LOGGER.debug("Hausnet switch state: '%s'", switch_state)

        if switch_state is None:
            self._available = False
            return

        self._is_on = switch_state.state == STATE_ON
        self._available = switch_state.state != STATE_UNAVAILABLE

    async def async_added_to_hass(self) -> None:
        @callback
        def async_state_changed_listener(entity_id: str, old_state: State,
                                         new_state: State):
            self.async_schedule_update_ha_state(True)

        self._async_unsub_state_changed = async_track_state_change(
            self.hass, self._switch_entity_id, async_state_changed_listener)

    async def async_will_remove_from_hass(self):
        if self._async_unsub_state_changed is not None:
            self._async_unsub_state_changed()
            self._async_unsub_state_changed = None
            self._available = False
"""
