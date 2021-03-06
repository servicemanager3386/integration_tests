# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.configure.configuration import Category, Tag
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.rest.gen_data import categories as _categories
from cfme.rest.gen_data import dialog as _dialog
from cfme.rest.gen_data import services as _services
from cfme.rest.gen_data import service_catalogs as _service_catalogs
from cfme.rest.gen_data import service_templates as _service_templates
from cfme.rest.gen_data import tenants as _tenants
from cfme.rest.gen_data import tags as _tags
from cfme.rest.gen_data import vm as _vm
from utils.update import update
from utils.wait import wait_for
from utils.version import current_version
from utils import error


@pytest.yield_fixture
def category():
    cg = Category(name=fauxfactory.gen_alphanumeric(8).lower(),
                  description=fauxfactory.gen_alphanumeric(32),
                  display_name=fauxfactory.gen_alphanumeric(32))
    cg.create()
    yield cg
    cg.delete()


@pytest.mark.tier(2)
def test_tag_crud(category):
    tag = Tag(name=fauxfactory.gen_alphanumeric(8).lower(),
              display_name=fauxfactory.gen_alphanumeric(32),
              category=category)
    tag.create()
    with update(tag):
        tag.display_name = fauxfactory.gen_alphanumeric(32)
    tag.delete(cancel=False)


class TestTagsViaREST(object):

    COLLECTIONS_BULK_TAGS = ("services", "vms")

    @pytest.fixture(scope="function")
    def categories(self, request, rest_api, num=3):
        return _categories(request, rest_api, num)

    @pytest.fixture(scope="function")
    def tags(self, request, rest_api, categories):
        return _tags(request, rest_api, categories)

    @pytest.fixture(scope="module")
    def categories_mod(self, request, rest_api_modscope, num=3):
        return _categories(request, rest_api_modscope, num)

    @pytest.fixture(scope="module")
    def tags_mod(self, request, rest_api_modscope, categories_mod):
        return _tags(request, rest_api_modscope, categories_mod)

    @pytest.fixture(scope="module")
    def service_catalogs(self, request, rest_api_modscope):
        return _service_catalogs(request, rest_api_modscope)

    @pytest.fixture(scope="module")
    def tenants(self, request, rest_api_modscope):
        return _tenants(request, rest_api_modscope, num=1)

    @pytest.fixture(scope="module")
    def a_provider(self, request):
        return _a_provider(request)

    @pytest.fixture(scope="module")
    def dialog(self):
        return _dialog()

    @pytest.fixture(scope="module")
    def services(self, request, rest_api_modscope, a_provider, dialog, service_catalogs):
        try:
            return _services(request, rest_api_modscope, a_provider, dialog, service_catalogs)
        except:
            pass

    def service_body(self, **kwargs):
        uid = fauxfactory.gen_alphanumeric(5)
        body = {
            'name': 'test_rest_service_{}'.format(uid),
            'description': 'Test REST Service {}'.format(uid),
        }
        body.update(kwargs)
        return body

    @pytest.fixture(scope="module")
    def dummy_services(self, request, rest_api_modscope):
        # create simple service using REST API
        bodies = [self.service_body() for _ in range(3)]
        collection = rest_api_modscope.collections.services
        new_services = collection.action.create(*bodies)
        assert rest_api_modscope.response.status_code == 200

        @request.addfinalizer
        def _finished():
            collection.reload()
            ids = [service.id for service in new_services]
            delete_entities = [service for service in collection if service.id in ids]
            if len(delete_entities) != 0:
                collection.action.delete(*delete_entities)

        return new_services

    @pytest.fixture(scope="module")
    def service_templates(self, request, rest_api_modscope, dialog):
        return _service_templates(request, rest_api_modscope, dialog)

    @pytest.fixture(scope="module")
    def vm(self, request, a_provider, rest_api_modscope):
        return _vm(request, a_provider, rest_api_modscope)

    @pytest.mark.tier(2)
    def test_edit_tags(self, rest_api, tags):
        """Tests tags editing from collection.

        Metadata:
            test_flag: rest
        """
        new_names = []
        tags_data_edited = []
        for tag in tags:
            new_name = "test_tag_{}".format(fauxfactory.gen_alphanumeric().lower())
            new_names.append(new_name)
            tag.reload()
            tags_data_edited.append({
                "href": tag.href,
                "name": new_name,
            })
        rest_api.collections.tags.action.edit(*tags_data_edited)
        assert rest_api.response.status_code == 200
        for new_name in new_names:
            wait_for(
                lambda: rest_api.collections.tags.find_by(name=new_name),
                num_sec=180,
                delay=10,
            )

    @pytest.mark.tier(2)
    def test_edit_tag(self, rest_api, tags):
        """Tests tag editing from detail.

        Metadata:
            test_flag: rest
        """
        tag = rest_api.collections.tags.get(name=tags[0].name)
        new_name = 'test_tag_{}'.format(fauxfactory.gen_alphanumeric())
        tag.action.edit(name=new_name)
        assert rest_api.response.status_code == 200
        wait_for(
            lambda: rest_api.collections.tags.find_by(name=new_name),
            num_sec=180,
            delay=10,
        )

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_tags_from_detail(self, rest_api, tags, method):
        """Tests deleting tags from detail.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == "delete" else 200
        for tag in tags:
            tag.action.delete(force_method=method)
            assert rest_api.response.status_code == status
            with error.expected("ActiveRecord::RecordNotFound"):
                tag.action.delete(force_method=method)
            assert rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_delete_tags_from_collection(self, rest_api, tags):
        """Tests deleting tags from collection.

        Metadata:
            test_flag: rest
        """
        rest_api.collections.tags.action.delete(*tags)
        assert rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            rest_api.collections.tags.action.delete(*tags)
        assert rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_create_tag_with_wrong_arguments(self, rest_api):
        """Tests creating tags with missing category "id", "href" or "name".

        Metadata:
            test_flag: rest
        """
        data = {
            "name": "test_tag_{}".format(fauxfactory.gen_alphanumeric().lower()),
            "description": "test_tag_{}".format(fauxfactory.gen_alphanumeric().lower())
        }
        with error.expected("BadRequestError: Category id, href or name needs to be specified"):
            rest_api.collections.tags.action.create(data)
        assert rest_api.response.status_code == 400

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "collection_name", ["clusters", "hosts", "data_stores", "providers", "resource_pools",
        "services", "service_templates", "tenants", "vms"])
    def test_assign_and_unassign_tag(self, rest_api, tags_mod, a_provider, services,
            service_templates, tenants, vm, collection_name):
        """Tests assigning and unassigning tags.

        Metadata:
            test_flag: rest
        """
        collection = getattr(rest_api.collections, collection_name)
        collection.reload()
        if len(collection.all) == 0:
            pytest.skip("No available entity in {} to assign tag".format(collection_name))
        entity = collection[-1]
        tag = tags_mod[0]
        entity.tags.action.assign(tag)
        assert rest_api.response.status_code == 200
        entity.reload()
        assert tag.id in [t.id for t in entity.tags.all]
        entity.tags.action.unassign(tag)
        assert rest_api.response.status_code == 200
        entity.reload()
        assert tag.id not in [t.id for t in entity.tags.all]

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "collection_name", COLLECTIONS_BULK_TAGS)
    def test_bulk_assign_and_unassign_tag(self, rest_api, tags_mod, dummy_services, vm,
            collection_name):
        """Tests bulk assigning and unassigning tags.

        Metadata:
            test_flag: rest
        """
        collection = getattr(rest_api.collections, collection_name)
        collection.reload()
        if len(collection) > 1:
            entities = [collection[-2], collection[-1]]  # slice notation doesn't work here
        else:
            entities = [collection[-1]]

        new_tags = []
        for index, tag in enumerate(tags_mod):
            identifiers = [{'href': tag._href}, {'id': tag.id}]
            new_tags.append(identifiers[index % 2])

        # add some more tags in supported formats
        new_tags.append({'category': 'department', 'name': 'finance'})
        new_tags.append({'name': '/managed/department/presales'})
        tags_ids = set([t.id for t in tags_mod])
        tags_ids.add(rest_api.collections.tags.get(name='/managed/department/finance').id)
        tags_ids.add(rest_api.collections.tags.get(name='/managed/department/presales').id)
        tags_count = len(new_tags) * len(entities)

        def _verify_action_result():
            assert rest_api.response.status_code == 200
            response = rest_api.response.json()
            assert len(response['results']) == tags_count
            num_success = 0
            for result in response['results']:
                if result['success']:
                    num_success += 1
            assert num_success == tags_count

        collection.action.assign_tags(*entities, tags=new_tags)
        _verify_action_result()
        for entity in entities:
            entity.tags.reload()
            assert len(tags_ids - set([t.id for t in entity.tags.all])) == 0

        collection.action.unassign_tags(*entities, tags=new_tags)
        _verify_action_result()
        for entity in entities:
            entity.tags.reload()
            assert len(set([t.id for t in entity.tags.all]) - tags_ids) == entity.tags.subcount

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "collection_name", COLLECTIONS_BULK_TAGS)
    def test_bulk_assign_and_unassign_invalid_tag(self, rest_api, dummy_services, vm,
            collection_name):
        """Tests bulk assigning and unassigning invalid tags.

        Metadata:
            test_flag: rest
        """
        collection = getattr(rest_api.collections, collection_name)
        collection.reload()
        if len(collection) > 1:
            entities = [collection[-2], collection[-1]]  # slice notation doesn't work here
        else:
            entities = [collection[-1]]

        new_tags = ['invalid_tag1', 'invalid_tag2']
        tags_count = len(new_tags) * len(entities)
        tags_per_entities_count = []
        for entity in entities:
            entity.tags.reload()
            tags_per_entities_count.append(entity.tags.subcount)

        def _verify_action_result():
            assert rest_api.response.status_code == 200
            response = rest_api.response.json()
            assert len(response['results']) == tags_count
            num_fail = 0
            for result in response['results']:
                if not result['success']:
                    num_fail += 1
            assert num_fail == tags_count

        def _check_tags_counts():
            for index, entity in enumerate(entities):
                entity.tags.reload()
                assert entity.tags.subcount == tags_per_entities_count[index]

        collection.action.assign_tags(*entities, tags=new_tags)
        _verify_action_result()
        _check_tags_counts()

        collection.action.unassign_tags(*entities, tags=new_tags)
        _verify_action_result()
        _check_tags_counts()
