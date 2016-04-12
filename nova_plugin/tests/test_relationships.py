"""Test the functions related to retrieving relationship information

Functions under test are mostly inside openstack_plugin_common:
get_relationships_by_openstack_type
get_connected_nodes_by_openstack_type
get_openstack_ids_of_connected_nodes_by_openstack_type
get_single_connected_node_by_openstack_type
"""

import uuid
from unittest import TestCase

from neutron_plugin.network import NETWORK_OPENSTACK_TYPE

from cloudify.exceptions import NonRecoverableError

from cloudify.mocks import (
    MockCloudifyContext,
    MockNodeContext,
    MockNodeInstanceContext,
    MockRelationshipContext,
    MockRelationshipSubjectContext,
)
from openstack_plugin_common import (
    OPENSTACK_ID_PROPERTY,
    OPENSTACK_TYPE_PROPERTY,
    get_openstack_id_of_single_connected_node_by_openstack_type,
    get_openstack_ids_of_connected_nodes_by_openstack_type,
    get_relationships_by_openstack_type,
    get_single_connected_node_by_openstack_type,
)


class TestGettingRelatedResources(TestCase):
    def _make_vm_ctx_with_relationships(self, rel_specs):
        """Prepare a mock CloudifyContext from the given relationship spec

        rel_specs is an ordered collection of relationship specs - dicts
        with the keys "node" and "instance" used to construct the
        MockNodeContext and the MockNodeInstanceContext, and optionally a
        "type" key.
        Examples: [
            {},
            {"node": {"id": 5}},
            {
                "type": "some_type",
                "instance": {
                    "id": 3,
                    "runtime_properties":{}
                }
            }
        ]
        """
        relationships = []
        for rel_spec in rel_specs:
            node = rel_spec.get('node', {})
            node_id = node.pop('id', uuid.uuid4().hex)

            instance = rel_spec.get('instance', {})
            instance_id = instance.pop('id', '{0}_{1}'.format(
                node_id, uuid.uuid4().hex))

            node_ctx = MockNodeContext(id=node_id, **node)
            instance_ctx = MockNodeInstanceContext(id=instance_id, **instance)

            rel_subject_ctx = MockRelationshipSubjectContext(
                node=node_ctx, instance=instance_ctx)
            rel_type = rel_spec.get('type')
            rel_ctx = MockRelationshipContext(target=rel_subject_ctx,
                                              type=rel_type)
            relationships.append(rel_ctx)
        return MockCloudifyContext(node_id='vm', relationships=relationships)

    def test_get_relationships(self):
        """get_relationships_by_openstack_type finds a rel by instance type
        """

        rel_spec = {
            'type': 'cloudify.relationships.connected_to',
            'instance': {
                'runtime_properties': {
                    OPENSTACK_TYPE_PROPERTY: NETWORK_OPENSTACK_TYPE
                }
            }
        }
        ctx = self._make_vm_ctx_with_relationships([rel_spec])
        filtered = get_relationships_by_openstack_type(ctx,
                                                       NETWORK_OPENSTACK_TYPE)

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].type,
                         'cloudify.relationships.connected_to')

    def test_get_relationships_finds_by_type(self):
        """get_relationships_by_openstack_type filters out other instance types
        """

        rel_spec = {
            'type': 'cloudify.relationships.connected_to',
            'instance': {
                'runtime_properties': {
                    OPENSTACK_TYPE_PROPERTY: 'something else'
                }
            }
        }
        ctx = self._make_vm_ctx_with_relationships([rel_spec])
        filtered = get_relationships_by_openstack_type(ctx,
                                                       NETWORK_OPENSTACK_TYPE)
        self.assertEqual(len(filtered), 0)

    def test_get_relationships_finds_all_by_type(self):
        """get_relationships_by_openstack_type returns all rels that match
        """

        rel_specs = [{
            'instance': {
                'id': instance_id,
                'runtime_properties': {
                    OPENSTACK_TYPE_PROPERTY: NETWORK_OPENSTACK_TYPE
                }
            }
        } for instance_id in range(3)]

        rel_specs.append({
            'instance': {
                'runtime_properties': {
                    OPENSTACK_TYPE_PROPERTY: 'something else'
                }
            }
        })

        ctx = self._make_vm_ctx_with_relationships(rel_specs)
        filtered = get_relationships_by_openstack_type(ctx,
                                                       NETWORK_OPENSTACK_TYPE)
        self.assertEqual(len(filtered), 3)

    def test_get_ids_of_nodes_by_type(self):

        rel_spec = {
            'instance': {
                'runtime_properties': {
                    OPENSTACK_TYPE_PROPERTY: NETWORK_OPENSTACK_TYPE,
                    OPENSTACK_ID_PROPERTY: 'the node id'
                }
            }
        }
        ctx = self._make_vm_ctx_with_relationships([rel_spec])
        ids = get_openstack_ids_of_connected_nodes_by_openstack_type(
            ctx, NETWORK_OPENSTACK_TYPE)
        self.assertEqual(ids, ['the node id'])

    def test_get_single_id(self):
        rel_spec = {
            'instance': {
                'runtime_properties': {
                    OPENSTACK_TYPE_PROPERTY: NETWORK_OPENSTACK_TYPE,
                    OPENSTACK_ID_PROPERTY: 'the node id'
                }
            }
        }
        ctx = self._make_vm_ctx_with_relationships([rel_spec])
        found_id = get_openstack_id_of_single_connected_node_by_openstack_type(
            ctx, NETWORK_OPENSTACK_TYPE)
        self.assertEqual(found_id, 'the node id')

    def test_get_single_id_two_found(self):
        rel_specs = [{
            'instance': {
                'runtime_properties': {
                    OPENSTACK_TYPE_PROPERTY: NETWORK_OPENSTACK_TYPE,
                    OPENSTACK_ID_PROPERTY: instance_id
                }
            }
        } for instance_id in range(2)]
        ctx = self._make_vm_ctx_with_relationships(rel_specs)
        self.assertRaises(
            NonRecoverableError,
            get_openstack_id_of_single_connected_node_by_openstack_type, ctx,
            NETWORK_OPENSTACK_TYPE)

    def test_get_single_id_two_found_if_exists_true(self):
        rel_specs = [{
            'instance': {
                'runtime_properties': {
                    OPENSTACK_TYPE_PROPERTY: NETWORK_OPENSTACK_TYPE,
                    OPENSTACK_ID_PROPERTY: instance_id
                }
            }
        } for instance_id in range(2)]
        ctx = self._make_vm_ctx_with_relationships(rel_specs)

        try:
            get_openstack_id_of_single_connected_node_by_openstack_type(
                ctx, NETWORK_OPENSTACK_TYPE, if_exists=True)
        except NonRecoverableError as e:
            self.assertIn(NETWORK_OPENSTACK_TYPE, e.message)
        else:
            self.fail()

    def test_get_single_id_if_exists_none_found(self):
        rel_spec = []
        ctx = self._make_vm_ctx_with_relationships(rel_spec)
        found = get_openstack_id_of_single_connected_node_by_openstack_type(
            ctx, NETWORK_OPENSTACK_TYPE, if_exists=True)
        self.assertIs(found, None)

    def test_get_single_id_none_found(self):
        rel_spec = []
        ctx = self._make_vm_ctx_with_relationships(rel_spec)
        self.assertRaises(
            NonRecoverableError,
            get_openstack_id_of_single_connected_node_by_openstack_type,
            ctx,
            NETWORK_OPENSTACK_TYPE)

    def test_get_single_node(self):
        rel_spec = {
            'node': {
                'id': 'the node id'
            },
            'instance': {
                'runtime_properties': {
                    OPENSTACK_TYPE_PROPERTY: NETWORK_OPENSTACK_TYPE
                }
            }
        }
        ctx = self._make_vm_ctx_with_relationships([rel_spec])
        found_node = get_single_connected_node_by_openstack_type(
            ctx, NETWORK_OPENSTACK_TYPE)
        self.assertEqual(found_node.id, 'the node id')

    def test_get_single_node_two_found(self):
        rel_spec = [{
            'node': {
                'id': node_id
            },
            'instance': {
                'runtime_properties': {
                    OPENSTACK_TYPE_PROPERTY: NETWORK_OPENSTACK_TYPE
                }
            }
        } for node_id in range(2)]
        ctx = self._make_vm_ctx_with_relationships(rel_spec)
        self.assertRaises(
            NonRecoverableError,
            get_single_connected_node_by_openstack_type,
            ctx, NETWORK_OPENSTACK_TYPE)

    def test_get_single_node_two_found_if_exists(self):
        rel_spec = [{
            'node': {
                'id': node_id
            },
            'instance': {
                'runtime_properties': {
                    OPENSTACK_TYPE_PROPERTY: NETWORK_OPENSTACK_TYPE
                }
            }
        } for node_id in range(2)]
        ctx = self._make_vm_ctx_with_relationships(rel_spec)
        self.assertRaises(
            NonRecoverableError,
            get_single_connected_node_by_openstack_type,
            ctx,
            NETWORK_OPENSTACK_TYPE,
            if_exists=True)

    def test_get_single_node_if_exists_none_found(self):
        rel_spec = []
        ctx = self._make_vm_ctx_with_relationships(rel_spec)
        found = get_single_connected_node_by_openstack_type(
            ctx, NETWORK_OPENSTACK_TYPE, if_exists=True)
        self.assertIs(found, None)

    def test_get_single_node_none_found(self):
        rel_spec = []
        ctx = self._make_vm_ctx_with_relationships(rel_spec)
        self.assertRaises(
            NonRecoverableError,
            get_single_connected_node_by_openstack_type,
            ctx,
            NETWORK_OPENSTACK_TYPE)
