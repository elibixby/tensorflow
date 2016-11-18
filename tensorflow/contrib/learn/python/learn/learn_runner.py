# Copyright 2016 The TensorFlow Authors. All Rights Reserved.
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
# ==============================================================================
"""Provides a wrapper which runs Estimator"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tensorflow.contrib.learn.python.learn.estimators import run_config
from tensorflow.contrib.learn.python.learn.experiment import Experiment
from tensorflow.python.platform import tf_logging as logging


def run(estimator,
        train_input_fn,
        eval_input_fn,
        schedule=None,
        train_input_args=None,
        train_input_kwargs=None,
        eval_input_args=None,
        eval_input_kwargs=None,
        eval_metrics=None,
        train_steps=None,
        eval_steps=100,
        train_monitors=None,
        local_eval_frequency=None,
        eval_delay_secs=120,
        continuous_eval_throttle_secs=60,
        min_eval_frequency=1,
        delay_workers_by_global_step=False):
  """Make and run an experiment.

  It creates an Experiment by calling `experiment_fn`. Then it calls the
  function named as `schedule` of the Experiment.

  If schedule is not provided, then the default schedule for the current task
  type is used. The defaults are as follows:

   * 'ps' maps to 'serve'
   * 'worker' maps to 'train'
   * 'master' maps to 'local_run'

  If the experiment's config does not include a task type, then an exception
  is raised.

  Example:
  ```
    def _create_my_experiment(output_dir):
        return tf.contrib.learn.Experiment(
          estimator=my_estimator(model_dir=output_dir),
          train_input_fn=my_train_input,
          eval_input_fn=my_eval_input)

    learn_runner.run(
      experiment_fn=_create_my_experiment,
      output_dir="some/output/dir",
      schedule="train")
  ```
  Args:
    experiment_fn: A function that creates an `Experiment`. It should accept an
      argument `output_dir` which should be used to create the `Estimator`
      (passed as `model_dir` to its constructor). It must return an
      `Experiment`.
    output_dir: Base output directory.
    schedule: The name of the  method in the `Experiment` to run.
    *experiment_fn_args: Any additional positional arguments are passed through
      to `experiment_fn` when it is called.
    **experiment_fn_kwargs: Any additional keyword arguments are passed through
      to `experiment_fn` when it is called.

  Returns:
    The return value of function `schedule`.

  Raises:
    ValueError: If `output_dir` is empty, `schedule` is None but no task
      type is set in the built experiment's config, the task type has no
      default, or `schedule` doesn't reference a member of `Experiment`.
    TypeError: `schedule` references non-callable member.
  """

  # Call the builder
  experiment = experiment_fn(output_dir=output_dir, *experiment_fn_args, **experiment_fn_kwargs)

  # Get the schedule
  config = config or _get_default_config()
  schedule = schedule or _get_default_schedule(config)

  # Execute the schedule
  if not hasattr(experiment, schedule):
    logging.error('Schedule references non-existent task %s', schedule)
    valid_tasks = [x for x in experiment.__dict__
                   if callable(getattr(experiment, x))]
    logging.error('Allowed values for this experiment are: %s', valid_tasks)
    raise ValueError('Schedule references non-existent task %s', schedule)

  task = getattr(experiment, schedule)
  if not callable(task):
    logging.error('Schedule references non-callable member %s', schedule)
    valid_tasks = [
        x for x in experiment.__dict__
        if callable(getattr(experiment, x)) and not x.startswith('_')
    ]
    logging.error('Allowed values for this experiment are: %s', valid_tasks)
    raise TypeError('Schedule references non-callable member %s', schedule)

  return task()


def train_and_evaluate()

def _get_default_config():
  pass

def _is_distributed(config):
  """Returns true if this is a distributed job."""
  if not config.cluster_spec:
    return False

  # This is considered a distributed job if there is more than one task
  # in the cluster spec.
  task_count = 0
  for job in config.cluster_spec.jobs:
    for _ in config.cluster_spec.job_tasks(job):
      task_count += 1

  return task_count > 1


def _get_default_schedule(config):
  """Returns the default schedule for the provided RunConfig."""
  if not config or not _is_distributed(config):
    return 'train_and_evaluate'

  if not config.task_type:
    raise ValueError('Must specify a schedule')

  if config.task_type == run_config.TaskType.MASTER:
    # TODO(rhaertel): handle the case where there is more than one master
    # or explicitly disallow such a case.
    return 'train_and_evaluate'
  elif config.task_type == run_config.TaskType.PS:
    return 'run_std_server'
  elif config.task_type == run_config.TaskType.WORKER:
    return 'train'

  raise ValueError('No default schedule for task type: %s' % (config.task_type))
