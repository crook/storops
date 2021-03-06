# coding=utf-8
# Copyright (c) 2015 EMC Corporation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from __future__ import unicode_literals

from unittest import TestCase

from hamcrest import assert_that, raises, equal_to, has_items, \
    only_contains

from test.vnx.cli_mock import t_cli, patch_cli
from test.vnx.resource.verifiers import verify_pool_0
from storops.exception import VNXCreatePoolError, VNXPoolNotFoundError, \
    VNXDiskUsedError, VNXPoolNameInUseError, VNXPoolDestroyingError
from storops.vnx.resource.block_pool import VNXPool, VNXPoolList, \
    VNXPoolFeature

__author__ = 'Cedric Zhuang'


class VNXPoolTest(TestCase):
    @staticmethod
    def get_pool_with_id(pool_id=0):
        return VNXPool(pool_id=pool_id, cli=t_cli())

    @staticmethod
    def get_pool_with_name(name='Pool4File'):
        return VNXPool(name=name, cli=t_cli())

    @patch_cli()
    def test_property_not_exist(self):
        def f():
            pool = VNXPool(pool_id=0)
            getattr(pool, '_abc')

        assert_that(f, raises(AttributeError))

    @patch_cli()
    def test_pool_by_id(self):
        pool = self.get_pool_with_id()
        verify_pool_0(pool)

    @patch_cli()
    def test_get_pool_get_all(self):
        pools = VNXPool.get(t_cli())
        assert_that(len(pools), equal_to(5))

    @patch_cli()
    def test_get_pool_from_list(self):
        pools = VNXPool.get(t_cli())
        pool = next(p for p in pools if p.pool_id == 4)
        # no error should be thrown here
        pool.update()

    @patch_cli()
    def test_get_pool_get_by_name(self):
        pool = VNXPool.get(t_cli(), name='Pool4File')
        verify_pool_0(pool)

    @patch_cli()
    def test_get_pool_get_by_id(self):
        pool = VNXPool.get(t_cli(), pool_id=0)
        verify_pool_0(pool)

    @patch_cli()
    def test_pool_by_name(self):
        pool = self.get_pool_with_name()
        verify_pool_0(pool)

    @patch_cli()
    def test_get_lun(self):
        pool = VNXPool(pool_id=1, cli=t_cli())
        assert_that(pool.name, equal_to('Pool_daq'))
        lun_list = pool.get_lun()
        assert_that(len(lun_list), equal_to(50))
        assert_that(pool.lun_list, equal_to(lun_list))
        assert_that(len(set(lun_list.pool_name)), equal_to(1))

    @patch_cli()
    def test_get_disk(self):
        pool = VNXPool(pool_id=1, cli=t_cli())
        disks = pool.disks
        assert_that(len(disks), equal_to(3))
        assert_that(disks.serial_number,
                    only_contains('6XS2EAKG', 'S0PFNECC304969', '6XS2QCG1'))

    @patch_cli()
    def test_create_pool_success(self):
        def f():
            VNXPool.create(t_cli(), 'p0', ['1_0_0', '1_0_1'])

        assert_that(f, raises(VNXCreatePoolError,
                              'less than minimum required'))

    @patch_cli()
    def test_create_pool_name_in_use_0(self):
        def f():
            VNXPool.create(t_cli(), 'p0', ['1_0_0', '1_0_1'], 'r_6')

        assert_that(f, raises(VNXPoolNameInUseError, 'already in use'))

    @patch_cli()
    def test_create_pool_name_in_use_1(self):
        def f():
            VNXPool.create(t_cli(), 'p0', ['1_0_0', '1_0_1'], 'r_0')

        assert_that(f, raises(VNXPoolNameInUseError, 'name is already used'))

    @patch_cli()
    def test_create_pool_disk_used(self):
        def f():
            VNXPool.create(t_cli(), 'p0', ['1_0_0', '1_0_1'], 'r_10')

        assert_that(f, raises(VNXDiskUsedError, 'already part of'))

    @patch_cli()
    def test_create_pool_invalid_disk_number(self):
        def f():
            VNXPool.create(t_cli(), 'p0', ['1_0_0', '1_0_1'], 'r_5')

        assert_that(f, raises(VNXCreatePoolError, 'multiple of 5'))

    @patch_cli()
    def test_delete_pool_not_found(self):
        def f():
            VNXPool(0, cli=t_cli()).delete()

        assert_that(f, raises(VNXPoolNotFoundError, 'may not exist'))

    @patch_cli()
    def test_delete_pool_destroying(self):
        def f():
            VNXPool(1, cli=t_cli()).delete()

        assert_that(f, raises(VNXPoolDestroyingError, 'is Destroying'))

    @patch_cli()
    def test_force_delete_pool(self):
        def f():
            VNXPool(0, cli=t_cli()).delete(True)

        assert_that(f, raises(VNXPoolNotFoundError, 'may not exist'))

    @patch_cli()
    def test_update_with_one_key_only(self):
        pool = VNXPool(0, 'p0', t_cli())
        assert_that(pool.consumed_capacity_gbs, equal_to(540.303))

    @patch_cli()
    def test_create_lun_ignore_threshold(self):
        def f():
            pool = VNXPool(1, cli=t_cli())
            pool.create_lun('abc', ignore_thresholds=True)

        assert_that(f, raises(VNXPoolNotFoundError, 'may not exist'))

    @patch_cli()
    def test_create_lun_with_pool_name(self):
        def f():
            pool = VNXPool(name='p0', cli=t_cli())
            pool.create_lun(lun_id=12)

        assert_that(f, raises(VNXPoolNotFoundError, 'may not exist'))


class VNXPoolListTest(TestCase):
    @staticmethod
    def get_pool_list():
        return VNXPoolList(t_cli())

    @patch_cli()
    def test_pool_list(self):
        pools = self.get_pool_list()
        assert_that(len(pools), equal_to(5))

    @patch_cli()
    def test_update(self):
        pools = self.get_pool_list()
        pools.update()
        # call twice
        pools.update()
        assert_that(len(pools), equal_to(5))


class VNXPoolFeatureTest(TestCase):
    @patch_cli()
    def test_properties(self):
        f = VNXPoolFeature(t_cli())
        assert_that(f.is_virtual_provisioning_supported, equal_to(False))
        assert_that(f.max_pools, equal_to(40))
        assert_that(f.max_disks_per_pool, equal_to(746))
        assert_that(f.max_disks_for_all_pools, equal_to(746))
        assert_that(f.max_disks_per_operation, equal_to(120))
        assert_that(f.max_pool_luns, equal_to(2100))
        assert_that(f.min_pool_lun_size_blocks, equal_to(1))
        assert_that(f.max_pool_lun_size_blocks, equal_to(549755813888))
        assert_that(f.max_pool_lun_size_gbs, equal_to(262144.0))
        assert_that(f.total_number_of_pools, equal_to(4))
        assert_that(f.total_pool_luns, equal_to(3))
        assert_that(f.total_thin_luns, equal_to(2))
        assert_that(f.total_non_thin_luns, equal_to(1))
        assert_that(f.number_of_disks_used_in_pools, equal_to(15))
        assert_that(f.available_disks.index,
                    has_items('0_0_B8', '0_0_B9'))
        assert_that(f.background_operation_state, equal_to('None'))
        assert_that(f.background_rate, equal_to('Medium'))

    @patch_cli()
    def test_available_disks(self):
        f = VNXPoolFeature(t_cli())
        assert_that(len(f.available_disks), equal_to(5))
