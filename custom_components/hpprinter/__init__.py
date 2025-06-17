import logging
import sys

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.core import HomeAssistant

from .common.consts import (
    DEFAULT_NAME,
    DOMAIN,
    INTERNAL_PRINT_ENDPOINT,
    CLEAN_CARTRIDGE_XML,
    DEEP_CLEAN_CARTRIDGE_XML,
    PRINT_TEST_PAGE_XML
)
from .managers.ha_config_manager import HAConfigManager
from .managers.ha_coordinator import HACoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(_hass, _config):
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Shinobi Video component."""
    initialized = False

    try:
        entry_config = {key: entry.data[key] for key in entry.data}

        config_manager = HAConfigManager(hass, entry)
        await config_manager.initialize(entry_config)

        is_initialized = config_manager.is_initialized

        if is_initialized:
            coordinator = HACoordinator(hass, config_manager)

            hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

            if hass.is_running:
                await coordinator.initialize()

            else:
                hass.bus.async_listen_once(
                    EVENT_HOMEASSISTANT_START, coordinator.on_home_assistant_start
                )

            async def _call_internal_print_dyn(coordinator, xml_body):
                await coordinator.api._post_request(
                    INTERNAL_PRINT_ENDPOINT, data=xml_body, headers={"Content-Type": "text/xml"}
                )

            async def async_handle_clean_cartridge_service(call):
                entry_id = call.data.get("entry")
                coordinator = hass.data[DOMAIN][entry_id]
                await _call_internal_print_dyn(coordinator, CLEAN_CARTRIDGE_XML)

            async def async_handle_deep_clean_cartridge_service(call):
                entry_id = call.data.get("entry")
                coordinator = hass.data[DOMAIN][entry_id]
                await _call_internal_print_dyn(coordinator, DEEP_CLEAN_CARTRIDGE_XML)

            async def async_handle_print_test_page_service(call):
                entry_id = call.data.get("entry")
                coordinator = hass.data[DOMAIN][entry_id]
                await _call_internal_print_dyn(coordinator, PRINT_TEST_PAGE_XML)
                
            hass.services.async_register(
                DOMAIN, "clean_cartridges", async_handle_clean_cartridge_service
            )
            hass.services.async_register(
                DOMAIN, "deep_clean_cartridges", async_handle_deep_clean_cartridge_service
            )
            hass.services.async_register(
                DOMAIN, "print_test_page", async_handle_print_test_page_service
            )

            _LOGGER.info("Finished loading integration")

        initialized = is_initialized

    except Exception as ex:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(
            f"Failed to load {DEFAULT_NAME}, error: {ex}, line: {line_number}"
        )

    return initialized


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.info(f"Unloading {DOMAIN} integration, Entry ID: {entry.entry_id}")

    coordinator: HACoordinator = hass.data[DOMAIN][entry.entry_id]

    await coordinator.config_manager.remove(entry.entry_id)

    platforms = coordinator.config_manager.platforms

    for platform in platforms:
        await hass.config_entries.async_forward_entry_unload(entry, platform)

    del hass.data[DOMAIN][entry.entry_id]

    return True
