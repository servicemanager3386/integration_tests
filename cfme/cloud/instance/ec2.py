from utils import version, deferred_verpick
from cfme.exceptions import OptionNotAvailable
from cfme.web_ui import fill, flash
from cfme.fixtures import pytest_selenium as sel
from . import Instance, select_provision_image


class EC2Instance(Instance):
    # CFME & provider power control options
    START = "Start"
    POWER_ON = START  # For compatibility with the infra objects.
    STOP = "Stop"
    DELETE = "Delete"
    TERMINATE = deferred_verpick({
        version.LOWEST: 'Terminate',
        '5.6.1': 'Delete',
    })
    # CFME-only power control options
    SOFT_REBOOT = "Soft Reboot"
    # Provider-only power control options
    RESTART = "Restart"

    # CFME power states
    STATE_ON = "on"
    STATE_OFF = "off"
    STATE_SUSPENDED = "suspended"
    STATE_TERMINATED = "terminated"
    STATE_ARCHIVED = "archived"
    STATE_UNKNOWN = "unknown"
    UI_POWERSTATES_AVAILABLE = {
        'on': [STOP, SOFT_REBOOT, TERMINATE],
        'off': [START, TERMINATE]
    }
    UI_POWERSTATES_UNAVAILABLE = {
        'on': [START],
        'off': [STOP, SOFT_REBOOT]
    }

    def create(self, email=None, first_name=None, last_name=None, availability_zone=None,
               security_groups=None, instance_type=None, guest_keypair=None, cancel=False,
               **prov_fill_kwargs):
        """Provisions an EC2 instance with the given properties through CFME

        Args:
            email: Email of the requester
            first_name: Name of the requester
            last_name: Surname of the requester
            availability_zone: Name of the zone the instance should belong to
            security_groups: List of security groups the instance should belong to
                             (currently, only the first one will be used)
            instance_type: Type of the instance
            guest_keypair: Name of the key pair used to access the instance
            cancel: Clicks the cancel button if `True`, otherwise clicks the submit button
                    (Defaults to `False`)
        Note:
            For more optional keyword arguments, see
            :py:data:`cfme.cloud.provisioning.provisioning_form`
        """
        from cfme.provisioning import provisioning_form
        # Nav to provision form and select image
        select_provision_image(template_name=self.template_name, provider=self.provider)

        fill(provisioning_form, dict(
            email=email,
            first_name=first_name,
            last_name=last_name,
            instance_name=self.name,
            availability_zone=availability_zone,
            # not supporting multiselect now, just take first value
            security_groups=security_groups[0],
            instance_type=instance_type,
            guest_keypair=guest_keypair,
            **prov_fill_kwargs
        ))

        if cancel:
            sel.click(provisioning_form.cancel_button)
            flash.assert_success_message(
                "Add of new VM Provision Request was cancelled by the user")
        else:
            sel.click(provisioning_form.submit_button)
            flash.assert_success_message(
                "VM Provision Request was Submitted, you will be notified when your VMs are ready")

    def power_control_from_provider(self, option):
        """Power control the instance from the provider

        Args:
            option: power control action to take against instance

        Raises:
            OptionNotAvailable: option param must have proper value
        """
        if option == EC2Instance.START:
            self.provider.mgmt.start_vm(self.name)
        elif option == EC2Instance.STOP:
            self.provider.mgmt.stop_vm(self.name)
        elif option == EC2Instance.RESTART:
            self.provider.mgmt.restart_vm(self.name)
        elif option == EC2Instance.TERMINATE:
            self.provider.mgmt.delete_vm(self.name)
        else:
            raise OptionNotAvailable(option + " is not a supported action")
