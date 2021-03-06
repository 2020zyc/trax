# coding=utf-8
# Copyright 2020 The Trax Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Lint as: python3
"""Tests for Trax base layer classes and generic layer-creating functions."""

from absl.testing import absltest

import numpy as np

from trax import math
from trax import shapes
from trax.layers import base
from trax.math import numpy as jnp


class BaseLayerTest(absltest.TestCase):

  def test_call_raises_error(self):
    layer = base.Layer()
    x = np.array([[1, 2, 3, 4, 5],
                  [10, 20, 30, 40, 50]])
    with self.assertRaisesRegex(base.LayerError, 'NotImplementedError'):
      _ = layer(x)

  def test_forward_raises_error(self):
    layer = base.Layer()
    x = np.array([[1, 2, 3, 4, 5],
                  [10, 20, 30, 40, 50]])
    with self.assertRaises(NotImplementedError):
      _ = layer.forward(x, base.EMPTY_WEIGHTS)

  def test_forward_with_state_raises_error(self):
    layer = base.Layer()
    x = np.array([[1, 2, 3, 4, 5],
                  [10, 20, 30, 40, 50]])
    with self.assertRaises(NotImplementedError):
      _, _ = layer.forward_with_state(
          x, base.EMPTY_WEIGHTS, base.EMPTY_STATE, None)

  def test_new_weights_returns_empty(self):
    layer = base.Layer()
    input_signature = shapes.ShapeDtype((2, 5))
    weights = layer.new_weights(input_signature)
    self.assertEmpty(weights)

  def test_new_weights_and_state_returns_empty(self):
    layer = base.Layer()
    input_signature = shapes.ShapeDtype((2, 5))
    weights, state = layer.new_weights_and_state(input_signature)
    self.assertEmpty(weights)
    self.assertEmpty(state)

  def test_init_returns_empty_weights_and_state(self):
    layer = base.Layer()
    input_signature = shapes.ShapeDtype((2, 5))
    weights, state = layer.init(input_signature)
    self.assertEmpty(weights)
    self.assertEmpty(state)

  def test_new_rng_deterministic(self):
    input_signature = shapes.ShapeDtype((2, 3, 5))
    layer1 = base.Layer()
    layer2 = base.Layer(n_in=2, n_out=2)
    _, _ = layer1.init(input_signature)
    _, _ = layer2.init(input_signature)
    rng1 = layer1.new_rng()
    rng2 = layer2.new_rng()
    self.assertEqual(rng1.tolist(), rng2.tolist())

  def test_new_rng_new_value_each_call(self):
    input_signature = shapes.ShapeDtype((2, 3, 5))
    layer = base.Layer()
    _, _ = layer.init(input_signature)
    rng1 = layer.new_rng()
    rng2 = layer.new_rng()
    rng3 = layer.new_rng()
    self.assertNotEqual(rng1.tolist(), rng2.tolist())
    self.assertNotEqual(rng2.tolist(), rng3.tolist())

  def test_new_rngs_deterministic(self):
    inputs1 = shapes.ShapeDtype((2, 3, 5))
    inputs2 = (shapes.ShapeDtype((2, 3, 5)), shapes.ShapeDtype((2, 3, 5)))
    layer1 = base.Layer()
    layer2 = base.Layer(n_in=2, n_out=2)
    _, _ = layer1.init(inputs1)
    _, _ = layer2.init(inputs2)
    rng1, rng2 = layer1.new_rngs(2)
    rng3, rng4 = layer2.new_rngs(2)
    self.assertEqual(rng1.tolist(), rng3.tolist())
    self.assertEqual(rng2.tolist(), rng4.tolist())

  def test_new_rngs_new_values_each_call(self):
    input_signature = shapes.ShapeDtype((2, 3, 5))
    layer = base.Layer()
    _, _ = layer.init(input_signature)
    rng1, rng2 = layer.new_rngs(2)
    rng3, rng4 = layer.new_rngs(2)
    self.assertNotEqual(rng1.tolist(), rng2.tolist())
    self.assertNotEqual(rng3.tolist(), rng4.tolist())
    self.assertNotEqual(rng1.tolist(), rng3.tolist())
    self.assertNotEqual(rng2.tolist(), rng4.tolist())

  def test_output_signature(self):
    input_signature = (shapes.ShapeDtype((2, 3, 5)),
                       shapes.ShapeDtype((2, 3, 5)))
    layer = base.Fn('2in1out', lambda x, y: x + y)
    output_signature = layer.output_signature(input_signature)
    self.assertEqual(output_signature, shapes.ShapeDtype((2, 3, 5)))

    input_signature = shapes.ShapeDtype((5, 7))
    layer = base.Fn('1in3out', lambda x: (x, 2 * x, 3 * x), n_out=3)
    output_signature = layer.output_signature(input_signature)
    self.assertEqual(output_signature, (shapes.ShapeDtype((5, 7)),) * 3)
    self.assertNotEqual(output_signature, (shapes.ShapeDtype((4, 7)),) * 3)
    self.assertNotEqual(output_signature, (shapes.ShapeDtype((5, 7)),) * 2)

  def test_custom_zero_grad(self):

    class IdWithZeroGrad(base.Layer):

      def forward(self, x, weights):
        return x

      @property
      def has_backward(self):
        return True

      def backward(self, inputs, output, grad, weights, state, new_state, rng):
        return (jnp.zeros_like(grad), ())

    layer = IdWithZeroGrad()
    rng = math.random.get_prng(0)
    input_signature = shapes.ShapeDtype((9, 17))
    random_input = math.random.uniform(rng, input_signature.shape,
                                       minval=-1.0, maxval=1.0)
    layer.init(input_signature)
    f = lambda x: jnp.mean(layer(x))
    grad = math.grad(f)(random_input)
    self.assertEqual(grad.shape, (9, 17))  # Gradient for each input.
    self.assertEqual(sum(sum(grad * grad)), 0.0)  # Each one is 0.

  def test_custom_id_grad(self):

    class IdWithIdGrad(base.Layer):

      def forward(self, x, weights):
        return x

      @property
      def has_backward(self):
        return True

      def backward(self, inputs, output, grad, weights, state, new_state, rng):
        return (inputs, ())

    layer = IdWithIdGrad()
    rng = math.random.get_prng(0)
    input_signature = shapes.ShapeDtype((9, 17))
    random_input = math.random.uniform(rng, input_signature.shape,
                                       minval=-1.0, maxval=1.0)
    layer.init(input_signature)
    f = lambda x: jnp.mean(layer(x))
    grad = math.grad(f)(random_input)
    self.assertEqual(grad.shape, (9, 17))  # Gradient for each input.
    self.assertEqual(sum(sum(grad)), sum(sum(random_input)))  # Same as input.

  def test_accelerated_forward_called_twice(self):

    class Constant(base.Layer):

      def new_weights(self, input_signature):
        return 123

      def forward(self, inputs, weights):
        return weights

    layer = Constant()
    layer.init(input_signature=shapes.ShapeDtype(()))
    layer(0, n_accelerators=1)
    layer(0, n_accelerators=1)

  def test_custom_name(self):
    layer = base.Layer()
    self.assertIn('Layer', str(layer))
    self.assertNotIn('CustomLayer', str(layer))

    layer = base.Layer(name='CustomLayer')
    self.assertIn('CustomLayer', str(layer))


class PureLayerTest(absltest.TestCase):

  def test_forward(self):
    layer = base.PureLayer(lambda x: 2 * x)

    # Use Layer.__call__.
    in_0 = np.array([1, 2])
    out_0 = layer(in_0)
    self.assertEqual(out_0.tolist(), [2, 4])

    # Use PureLayer.forward.
    in_1 = np.array([3, 4])
    out_1 = layer.forward(in_1, base.EMPTY_WEIGHTS)
    self.assertEqual(out_1.tolist(), [6, 8])

    # Use Layer.forward_with_state.
    in_2 = np.array([5, 6])
    out_2, _ = layer.forward_with_state(
        in_2, base.EMPTY_WEIGHTS, base.EMPTY_WEIGHTS, None)
    self.assertEqual(out_2.tolist(), [10, 12])


class FnTest(absltest.TestCase):

  def test_bad_f_has_default_arg(self):
    with self.assertRaisesRegex(ValueError, 'default arg'):
      _ = base.Fn('', lambda x, sth=None: x)

  def test_bad_f_has_keyword_arg(self):
    with self.assertRaisesRegex(ValueError, 'keyword arg'):
      _ = base.Fn('', lambda x, **kwargs: x)

  def test_bad_f_has_variable_arg(self):
    with self.assertRaisesRegex(ValueError, 'variable arg'):
      _ = base.Fn('', lambda *args: args[0])

  def test_forward(self):
    layer = base.Fn('SumAndMax',
                    lambda x0, x1: (x0 + x1, jnp.maximum(x0, x1)),
                    n_out=2)

    x0 = np.array([1, 2, 3, 4, 5])
    x1 = np.array([10, 20, 30, 40, 50])

    y0, y1 = layer((x0, x1))
    self.assertEqual(y0.tolist(), [11, 22, 33, 44, 55])
    self.assertEqual(y1.tolist(), [10, 20, 30, 40, 50])

    y2, y3 = layer.forward((x0, x1), base.EMPTY_WEIGHTS)
    self.assertEqual(y2.tolist(), [11, 22, 33, 44, 55])
    self.assertEqual(y3.tolist(), [10, 20, 30, 40, 50])

    (y4, y5), state = layer.forward_with_state(
        (x0, x1), base.EMPTY_WEIGHTS, base.EMPTY_STATE, None)
    self.assertEqual(y4.tolist(), [11, 22, 33, 44, 55])
    self.assertEqual(y5.tolist(), [10, 20, 30, 40, 50])
    self.assertEqual(state, base.EMPTY_STATE)

  def test_weights_state(self):
    layer = base.Fn(
        '2in2out',
        lambda x, y: (x + y, jnp.concatenate([x, y], axis=0)), n_out=2)
    weights, state = layer.new_weights_and_state(None)
    self.assertEmpty(weights)
    self.assertEmpty(state)


if __name__ == '__main__':
  absltest.main()
