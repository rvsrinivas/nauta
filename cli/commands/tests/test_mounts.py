#
# INTEL CONFIDENTIAL
# Copyright (c) 2018 Intel Corporation
#
# The source code contained or described herein and all documents related to
# the source code ("Material") are owned by Intel Corporation or its suppliers
# or licensors. Title to the Material remains with Intel Corporation or its
# suppliers and licensors. The Material contains trade secrets and proprietary
# and confidential information of Intel or its suppliers and licensors. The
# Material is protected by worldwide copyright and trade secret laws and treaty
# provisions. No part of the Material may be used, copied, reproduced, modified,
# published, uploaded, posted, transmitted, distributed, or disclosed in any way
# without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be express
# and approved by Intel in writing.
#

import platform

from click.testing import CliRunner

from commands.user.mounts import get_mount_command_linux, get_mount_command_windows, get_mount_command_osx, mounts

TEST_USR = "test_user"
TEST_PSW = "test_password"
TEST_ADR = "test_address"

CORRECT_LINUX_MOUNT = f"sudo mount.cifs -o username={TEST_USR},password=" \
                      f"{TEST_PSW},rw,uid=10001 //{TEST_ADR}/<DLS4E_FOLDER> <MOUNTPOINT>"

CORRECT_WINDOWS_MOUNT = f"net use \\\\{TEST_ADR}\\<DLS4E_FOLDER> /user:{TEST_USR} {TEST_PSW}"

CORRECT_OSX_MOUNT = f"mount_smbfs //'{TEST_USR}:{TEST_PSW}'@{TEST_ADR}/<DLS4E_FOLDER> <MOUNTPOINT>"


def test_get_mount_command_linux(mocker):
    # os library doesn't have getuid function on Windows
    if platform.system() != 'Windows':
        mocker.patch("os.getuid", return_value="10001")

        mount = get_mount_command_linux(TEST_USR, TEST_PSW, TEST_ADR)

        assert mount == CORRECT_LINUX_MOUNT
    else:
        assert True


def test_get_mount_command_windows(mocker):
    mount = get_mount_command_windows(TEST_USR, TEST_PSW, TEST_ADR)

    assert mount == CORRECT_WINDOWS_MOUNT


def test_get_mount_command_osx(mocker):
    mount = get_mount_command_osx(TEST_USR, TEST_PSW, TEST_ADR)

    assert mount == CORRECT_OSX_MOUNT


def test_mounts(mocker):
    host_system = platform.system()

    gcu_mock = mocker.patch("commands.user.mounts.get_current_user", return_value=TEST_USR)
    gus_mock = mocker.patch("commands.user.mounts.get_users_samba_password", return_value=TEST_PSW)
    cmp_mock = mocker.patch("commands.user.mounts.DLS4EConfigMap")

    cmp_mock.return_value.external_ip = TEST_ADR

    runner = CliRunner()
    # os library doesn't have getuid function on Windows
    if host_system != 'Windows':
        os_getuid_mock = mocker.patch("os.getuid", return_value="10001")

        mocker.patch("platform.system", return_value="Linux")

        result = runner.invoke(mounts)

        assert CORRECT_LINUX_MOUNT in result.output
        assert os_getuid_mock.call_count == 1

    mocker.patch("platform.system", return_value="Windows")

    result = runner.invoke(mounts)

    assert CORRECT_WINDOWS_MOUNT in result.output

    mocker.patch("platform.system", return_value="OSX")

    result = runner.invoke(mounts)

    assert CORRECT_OSX_MOUNT in result.output

    if host_system != 'Windows':
        call_number = 3
    else:
        call_number = 2

    assert gcu_mock.call_count == call_number
    assert gus_mock.call_count == call_number
    assert cmp_mock.call_count == call_number
