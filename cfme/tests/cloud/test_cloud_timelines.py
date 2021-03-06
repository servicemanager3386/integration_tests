# -*- coding: utf-8 -*-
import pytest

from cfme.cloud.availability_zone import AvailabilityZone
from cfme.cloud.instance import Instance
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from utils import testgen, version
from utils.appliance.implementations.ui import navigate_to
from utils.generators import random_vm_name
from utils.log import logger
from utils.wait import wait_for


pytestmark = [pytest.mark.tier(2),
              pytest.mark.uncollectif(lambda: version.current_version() < '5.7'),
              pytest.mark.usefixtures("setup_provider_modscope")]
pytest_generate_tests = testgen.generate([AzureProvider, OpenStackProvider], scope="module")


@pytest.fixture(scope="module")
def test_instance(request, provider):
    instance = Instance.factory(random_vm_name("timelines", max_length=16), provider)

    request.addfinalizer(instance.delete_from_provider)

    if not provider.mgmt.does_vm_exist(instance.name):
        logger.info("deploying %s on provider %s", instance.name, provider.key)
        instance.create_on_provider(allow_skip="default", find_in_cfme=True)
    return instance


@pytest.fixture(scope="module")
def gen_events(test_instance):
    logger.debug('Starting, stopping VM')
    mgmt = test_instance.provider.mgmt
    mgmt.stop_vm(test_instance.name)
    mgmt.start_vm(test_instance.name)


def count_events(target, vm):
    timelines_view = navigate_to(target, 'Timelines')
    timelines_view.filter.time_position.select_by_visible_text('centered')
    timelines_view.filter.apply.click()
    found_events = []
    for evt in timelines_view.chart.get_events():
        # BZ(1428797)
        if not hasattr(evt, 'source_instance'):
            logger.warn("event {evt!r} doesn't have source_vm field. "
                        "Probably issue".format(evt=evt))
            continue
        elif evt.source_instance == vm.name:
            found_events.append(evt)

    logger.info("found events: {evt}".format(evt="\n".join([repr(e) for e in found_events])))
    return len(found_events)


def test_provider_event(gen_events, test_instance):
    """ Tests provider events on timelines

    Metadata:
        test_flag: timelines, provision
    """
    wait_for(count_events, [test_instance.provider, test_instance], timeout='5m', fail_condition=0,
             message="events to appear")


def test_azone_event(gen_events, test_instance):
    """ Tests availability zone events on timelines

    Metadata:
        test_flag: timelines, provision
    """
    # obtaining this instance's azone
    zone_id = test_instance.get_vm_via_rest().availability_zone_id
    zones = test_instance.appliance.rest_api.collections.availability_zones
    zone_name = next(zone.name for zone in zones if zone.id == zone_id)
    azone = AvailabilityZone(name=zone_name, provider=test_instance.provider,
                             appliance=test_instance.appliance)
    wait_for(count_events, [azone, test_instance], timeout='5m', fail_condition=0,
             message="events to appear")


def test_vm_event(gen_events, test_instance):
    """ Tests vm events on timelines

    Metadata:
        test_flag: timelines, provision
    """
    wait_for(count_events, [test_instance, test_instance], timeout='5m', fail_condition=0,
             message="events to appear")
