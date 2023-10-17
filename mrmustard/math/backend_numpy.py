# Copyright 2023 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np

from .backend_base import BackendBase


class BackendNumpy(BackendBase):
    r"""
    A numpy backend.
    """

    int32 = np.int

    def __init__(self):
        super().__init__(name="numpy")

    def hello(self):
        print(f"Hello from {self._name}")
