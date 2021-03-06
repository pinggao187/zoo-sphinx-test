#
# Copyright 2018 Analytics Zoo Authors.
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
#
# Some portions of this file Copyright (c) 2017, Maxpoint
# and licensed under the BSD license.
#

from bigdl.util.common import *
from zoo.common.utils import callZooFunc
from zoo.util.utils import set_python_home
import warnings
import multiprocessing
import os

import threading
import sys


def init_spark_on_local(cores=2, conf=None, python_location=None, spark_log_level="WARN",
                        redirect_spark_log=True):
    """Saves the Trainer state to the provided checkpoint path.

    Args:

        checkpoint (str): Path to target checkpoint file.
    """
    from zoo.util.spark import SparkRunner
    runner = SparkRunner(spark_log_level=spark_log_level,
                         redirect_spark_log=redirect_spark_log)
    set_python_home()
    return runner.init_spark_on_local(cores=cores, conf=conf,
                                      python_location=python_location)


def init_spark_on_yarn(hadoop_conf,
                       conda_name,
                       num_executors,
                       executor_cores,
                       executor_memory="2g",
                       driver_cores=4,
                       driver_memory="1g",
                       extra_executor_memory_for_ray=None,
                       extra_python_lib=None,
                       penv_archive=None,
                       additional_archive=None,
                       hadoop_user_name="root",
                       spark_yarn_archive=None,
                       spark_log_level="WARN",
                       redirect_spark_log=True,
                       jars=None,
                       conf=None):
    """Returns the local TrainingOperator object.
    
       Be careful not to perturb its state, or else you can cause the system
       to enter an inconsistent state.
       
       Returns:
            TrainingOperator: The local TrainingOperator object.
    """
    from zoo.util.spark import SparkRunner
    runner = SparkRunner(spark_log_level=spark_log_level,
                         redirect_spark_log=redirect_spark_log)
    set_python_home()
    sc = runner.init_spark_on_yarn(
        hadoop_conf=hadoop_conf,
        conda_name=conda_name,
        num_executors=num_executors,
        executor_cores=executor_cores,
        executor_memory=executor_memory,
        driver_cores=driver_cores,
        driver_memory=driver_memory,
        extra_executor_memory_for_ray=extra_executor_memory_for_ray,
        extra_python_lib=extra_python_lib,
        penv_archive=penv_archive,
        additional_archive=additional_archive,
        hadoop_user_name=hadoop_user_name,
        spark_yarn_archive=spark_yarn_archive,
        jars=jars,
        conf=conf)
    return sc


def init_spark_standalone(num_executors,
                          executor_cores,
                          executor_memory="2g",
                          driver_cores=4,
                          driver_memory="1g",
                          master=None,
                          extra_executor_memory_for_ray=None,
                          extra_python_lib=None,
                          spark_log_level="WARN",
                          redirect_spark_log=True,
                          conf=None,
                          jars=None,
                          python_location=None,
                          enable_numa_binding=False):
    """Returns the local TrainingOperator object.

       Be careful not to perturb its state, or else you can cause the system
       to enter an inconsistent state.

       Returns:
            TrainingOperator: The local TrainingOperator object.
    """

    from zoo.util.spark import SparkRunner
    runner = SparkRunner(spark_log_level=spark_log_level,
                         redirect_spark_log=redirect_spark_log)
    set_python_home()
    sc = runner.init_spark_standalone(
        num_executors=num_executors,
        executor_cores=executor_cores,
        executor_memory=executor_memory,
        driver_cores=driver_cores,
        driver_memory=driver_memory,
        master=master,
        extra_executor_memory_for_ray=extra_executor_memory_for_ray,
        extra_python_lib=extra_python_lib,
        conf=conf,
        jars=jars,
        python_location=python_location,
        enable_numa_binding=enable_numa_binding)
    return sc


def init_spark_on_k8s(master,
                      container_image,
                      num_executors,
                      executor_cores,
                      executor_memory="2g",
                      driver_memory="1g",
                      driver_cores=4,
                      extra_executor_memory_for_ray=None,
                      extra_python_lib=None,
                      spark_log_level="WARN",
                      redirect_spark_log=True,
                      jars=None,
                      conf=None,
                      python_location=None):
    """Returns the local TrainingOperator object.

       Be careful not to perturb its state, or else you can cause the system
       to enter an inconsistent state.
       
       Args:
            num_steps (int): Number of batches to compute update steps on
                per worker. This corresponds also to the number of times
                ``TrainingOperator.validate_batch`` is called per worker.
            profile (bool): Returns time stats for the evaluation procedure.
            reduce_results (bool): Whether to average all metrics across
                all workers into one dict. If a metric is a non-numerical
                value (or nested dictionaries), one value will be randomly
                selected among the workers. If False, returns a list of dicts.
            info (dict): Optional dictionary passed to the training
                operator for `validate` and `validate_batch`.
       
        Returns:
            TrainingOperator: The local TrainingOperator object.
    """

    from zoo.util.spark import SparkRunner
    runner = SparkRunner(spark_log_level=spark_log_level,
                         redirect_spark_log=redirect_spark_log)
    sc = runner.init_spark_on_k8s(
        master=master,
        container_image=container_image,
        num_executors=num_executors,
        executor_cores=executor_cores,
        executor_memory=executor_memory,
        driver_memory=driver_memory,
        driver_cores=driver_cores,
        extra_executor_memory_for_ray=extra_executor_memory_for_ray,
        extra_python_lib=extra_python_lib,
        jars=jars,
        conf=conf,
        python_location=python_location)
    return sc


def stop_spark_standalone():
    """
    Stop the Spark standalone cluster created from init_spark_standalone (master not specified).
    """
    from zoo.util.spark import SparkRunner
    SparkRunner.stop_spark_standalone()


class ZooContextMeta(type):

    _log_output = False
    
    """Train a PyTorch model using distributed PyTorch.

    Launches a set of actors which connect via distributed PyTorch and
    coordinate gradient updates to train the provided model. If Ray is not
    initialized, TorchTrainer will automatically initialize a local Ray
    cluster for you. Be sure to run `ray.init(address="auto")` to leverage
    multi-node training.

    .. code-block:: python

        class MyTrainingOperator(TrainingOperator):
            def setup(self, config):
                model = nn.Linear(1, 1)
                optimizer = torch.optim.SGD(
                    model.parameters(), lr=config.get("lr", 1e-4))
                loss = torch.nn.MSELoss()
                batch_size = config["batch_size"]
                train_data, val_data = LinearDataset(2, 5), LinearDataset(2, 5)
                train_loader = DataLoader(train_data, batch_size=batch_size)
                val_loader = DataLoader(val_data, batch_size=batch_size)
                self.model, self.optimizer = self.register(
                    models=model,
                    optimizers=optimizer,
                    criterion=loss)
                self.register_data(
                    train_loader=train_loader,
                    validation_loader=val_loader)
        trainer = TorchTrainer(
            training_operator_cls=MyTrainingOperator,
            config={"batch_size": 32},
            use_gpu=True
        )
        for i in range(4):
            trainer.train()

    Args:
        training_operator_cls (type): Custom training operator class
            that subclasses the TrainingOperator class. This class
            will be copied onto all remote workers and used to specify
            training components and custom training and validation operations.
        initialization_hook (function): A function to call on all training
            workers when they are first initialized. This could be useful to
            set environment variables for all the worker processes.
        config (dict): Custom configuration value to be passed to
            all operator constructors.
        num_workers (int): the number of workers used in distributed
            training. If 1, the worker will not be wrapped with
            DistributedDataParallel. TorchTrainer will scale down the number
            of workers if enough resources are not available, and will scale
            back up once they are. The total number of
            workers will never exceed `num_workers` amount.
    
    """

    @property
    def log_output(cls):
        """
        Whether to redirect Spark driver JVM's stdout and stderr to the current
        python process. This is useful when running Analytics Zoo in jupyter notebook.
        Default to be False. Needs to be set before initializing SparkContext.
        """
        return cls._log_output

    @log_output.setter
    def log_output(cls, value):
        if SparkContext._active_spark_context is not None:
            raise AttributeError("log_output cannot be set after SparkContext is created."
                                 " Please set it before init_nncontext, init_spark_on_local"
                                 "or init_spark_on_yarn")
        assert isinstance(value, bool), "log_output should either be True or False"
        cls._log_output = value


class ZooContext(metaclass=ZooContextMeta):
    """Train a PyTorch model using distributed PyTorch.

    Launches a set of actors which connect via distributed PyTorch and
    coordinate gradient updates to train the provided model. If Ray is not
    initialized, TorchTrainer will automatically initialize a local Ray
    cluster for you. Be sure to run `ray.init(address="auto")` to leverage
    multi-node training.

    Args:
        training_operator_cls (type): Custom training operator class
            that subclasses the TrainingOperator class. This class
            will be copied onto all remote workers and used to specify
            training components and custom training and validation operations.
        initialization_hook (function): A function to call on all training
            workers when they are first initialized. This could be useful to
            set environment variables for all the worker processes.
        config (dict): Custom configuration value to be passed to
            all operator constructors.
        num_workers (int): the number of workers used in distributed
            training. If 1, the worker will not be wrapped with
            DistributedDataParallel. TorchTrainer will scale down the number
            of workers if enough resources are not available, and will scale
            back up once they are. The total number of
            workers will never exceed `num_workers` amount.
    """

    pass


# The following function copied from
# https://github.com/Valassis-Digital-Media/spylon-kernel/blob/master/
# spylon_kernel/scala_interpreter.py
def _read_stream(fd, fn):
    """Reads bytes from a file descriptor, utf-8 decodes them, and passes them
    to the provided callback function on the next IOLoop tick.
    Assumes fd.read will block and should be used in a thread.
    
    """
    while True:
        # Specify a max read size so the read doesn't block indefinitely
        # Using a value less than the typical default max pipe size
        # and greater than a single system page.
        buff = fd.read(8192)
        if buff:
            fn(buff.decode('utf-8'))


def init_nncontext(conf=None, spark_log_level="WARN", redirect_spark_log=True):
    
    # The following code copied and modified from
    # https://github.com/Valassis-Digital-Media/spylon-kernel/blob/master/
    # spylon_kernel/scala_interpreter.py
    if ZooContext.log_output:
        import subprocess
        import pyspark.java_gateway
        spark_jvm_proc = None
        """Returns the local TrainingOperator object.

       Be careful not to perturb its state, or else you can cause the system
       to enter an inconsistent state.

       Returns:
            TrainingOperator: The local TrainingOperator object.
   
       """

        def Popen(*args, **kwargs):
            """Wraps subprocess.Popen to force stdout and stderr from the child process
            to pipe to this process without buffering.
            """
            nonlocal spark_jvm_proc
            # Override these in kwargs to avoid duplicate value errors
            # Set streams to unbuffered so that we read whatever bytes are available
            # when ready, https://docs.python.org/3.6/library/subprocess.html#popen-constructor
            kwargs['bufsize'] = 0
            # Capture everything from stdout for display in the notebook
            kwargs['stdout'] = subprocess.PIPE
            # Optionally capture stderr, otherwise it'll go to the kernel log
            kwargs['stderr'] = subprocess.PIPE
            spark_jvm_proc = subprocess.Popen(*args, **kwargs)
            return spark_jvm_proc

        pyspark.java_gateway.Popen = Popen

    if isinstance(conf, six.string_types):
        sc = getOrCreateSparkContext(conf=None, appName=conf)
    else:
        sc = getOrCreateSparkContext(conf=conf)
    sc.setLogLevel(spark_log_level)

    if ZooContext.log_output:
        if spark_jvm_proc.stdout is not None:
            stdout_reader = threading.Thread(target=_read_stream,
                                             daemon=True,
                                             kwargs=dict(
                                                 fd=spark_jvm_proc.stdout,
                                                 fn=sys.stdout.write))
            stdout_reader.start()
        if spark_jvm_proc.stderr is not None:
            stderr_reader = threading.Thread(target=_read_stream,
                                             daemon=True,
                                             kwargs=dict(
                                                 fd=spark_jvm_proc.stderr,
                                                 fn=sys.stderr.write))
            stderr_reader.start()
    check_version()
    if redirect_spark_log:
        redire_spark_logs()
        show_bigdl_info_logs()
    init_engine()
    set_python_home()
    return sc


def getOrCreateSparkContext(conf=None, appName=None):
    """
    Get the current active SparkContext or create a new SparkContext.
    :param conf: An instance of SparkConf. If not specified, a new SparkConf with
           Analytics Zoo and BigDL configurations would be created and used.
    :param appName: The name of the application if any.

    Returns:
            A dictionary of metrics for validation.
                You can provide custom metrics by passing in a custom
                ``training_operator_cls``.
    """
    with SparkContext._lock:
        if SparkContext._active_spark_context is None:
            spark_conf = init_spark_conf() if conf is None else conf
            if appName:
                spark_conf.setAppName(appName)
            return SparkContext.getOrCreate(spark_conf)
        else:
            return SparkContext.getOrCreate()


def get_analytics_zoo_conf():
    zoo_conf_file = "spark-analytics-zoo.conf"
    zoo_python_wrapper = "python-api.zip"
    """
    Get the current active SparkContext or create a new SparkContext.
    :param conf: An instance of SparkConf. If not specified, a new SparkConf with
           Analytics Zoo and BigDL configurations would be created and used.
    :param appName: The name of the application if any.

    Returns:
            A dictionary of metrics for validation.
                You can provide custom metrics by passing in a custom
                ``training_operator_cls``.
    """

    for p in sys.path:
        if zoo_conf_file in p and os.path.isfile(p):
            with open(p) if sys.version_info < (3,) else open(p, encoding='latin-1') as conf_file:
                return load_conf(conf_file.read())
        if zoo_python_wrapper in p and os.path.isfile(p):
            import zipfile
            with zipfile.ZipFile(p, 'r') as zip_conf:
                if zoo_conf_file in zip_conf.namelist():
                    content = zip_conf.read(zoo_conf_file)
                    if sys.version_info >= (3,):
                        content = str(content, 'latin-1')
                    return load_conf(content)
    return {}


def init_env(conf):
    # Default env
    kmp_affinity = "granularity=fine,compact,1,0"
    kmp_settings = "1"
    omp_num_threads = "1"
    kmp_blocktime = "0"
    """
    Get the current active SparkContext or create a new SparkContext.
    :param conf: An instance of SparkConf. If not specified, a new SparkConf with
           Analytics Zoo and BigDL configurations would be created and used.
    :param appName: The name of the application if any.

    Returns:
            A dictionary of metrics for validation.
                You can provide custom metrics by passing in a custom
                ``training_operator_cls``.
    """

    # Check env and override if necessary
    # Currently, focused on ZOO_NUM_MKLTHREADS,
    # OMP_NUM_THREADS, KMP_BLOCKTIME, KMP_AFFINITY
    # and KMP_SETTINGS
    if "KMP_AFFINITY" in os.environ:
        kmp_affinity = os.environ["KMP_AFFINITY"]
    if "KMP_SETTINGS" in os.environ:
        kmp_settings = os.environ["KMP_SETTINGS"]
    if "ZOO_NUM_MKLTHREADS" in os.environ:
        if os.environ["ZOO_NUM_MKLTHREADS"].lower() == "all":
            omp_num_threads = conf.get('spark.executor.cores', str(multiprocessing.cpu_count()))
        else:
            omp_num_threads = os.environ["ZOO_NUM_MKLTHREADS"]
    elif "OMP_NUM_THREADS" in os.environ:
        omp_num_threads = os.environ["OMP_NUM_THREADS"]
    if "KMP_BLOCKTIME" in os.environ:
        kmp_blocktime = os.environ["KMP_BLOCKTIME"]

    # Set env
    conf.set("spark.executorEnv.KMP_AFFINITY", kmp_affinity)
    conf.set("spark.executorEnv.KMP_SETTINGS", kmp_settings)
    conf.set("spark.executorEnv.KMP_BLOCKTIME", kmp_blocktime)
    conf.set("spark.executorEnv.OMP_NUM_THREADS", omp_num_threads)
    os.environ["KMP_AFFINITY"] = kmp_affinity
    os.environ["KMP_SETTINGS"] = kmp_settings
    os.environ["OMP_NUM_THREADS"] = omp_num_threads
    os.environ["KMP_BLOCKTIME"] = kmp_blocktime


def init_spark_conf(conf=None):
    spark_conf = SparkConf()
    if conf:
        spark_conf.setAll(conf.items())
    init_env(spark_conf)
    zoo_conf = get_analytics_zoo_conf()
    # Set bigDL and TF conf
    spark_conf.setAll(zoo_conf.items())
    """
    Get the current active SparkContext or create a new SparkContext.
    :param conf: An instance of SparkConf. If not specified, a new SparkConf with
           Analytics Zoo and BigDL configurations would be created and used.
    :param appName: The name of the application if any.

    Returns:
            A dictionary of metrics for validation.
                You can provide custom metrics by passing in a custom
                ``training_operator_cls``.
    """

    if os.environ.get("BIGDL_JARS", None) and not is_spark_below_2_2():
        if 'PYSPARK_SUBMIT_ARGS' in os.environ:
            submit_args = os.environ['PYSPARK_SUBMIT_ARGS']
            start = submit_args.find('pyspark-shell')
            submit_args = '{}--driver-class-path {} {}'.format(submit_args[:start],
                                                               os.environ["BIGDL_JARS"],
                                                               submit_args[start:])
        else:
            submit_args = " --driver-class-path " + os.environ["BIGDL_JARS"] + " pyspark-shell "
        print("pyspark_submit_args is: {}".format(submit_args))
        os.environ['PYSPARK_SUBMIT_ARGS'] = submit_args

    # add content in PYSPARK_FILES in spark.submit.pyFiles
    # This is a workaround for current Spark on k8s
    python_lib = os.environ.get('PYSPARK_FILES', None)
    if python_lib:
        existing_py_files = spark_conf.get("spark.submit.pyFiles")
        if existing_py_files:
            spark_conf.set(key="spark.submit.pyFiles",
                           value="%s,%s" % (python_lib, existing_py_files))
        else:
            spark_conf.set(key="spark.submit.pyFiles", value=python_lib)

    return spark_conf


def check_version():
    sc = getOrCreateSparkContext()
    conf = sc._conf
    """
    Get the current active SparkContext or create a new SparkContext.
    :param conf: An instance of SparkConf. If not specified, a new SparkConf with
           Analytics Zoo and BigDL configurations would be created and used.
    :param appName: The name of the application if any.

    Returns:
            A dictionary of metrics for validation.
                You can provide custom metrics by passing in a custom
                ``training_operator_cls``.
    """

    if conf.get("spark.analytics.zoo.versionCheck", "False").lower() == "true":
        report_warn = conf.get(
            "spark.analytics.zoo.versionCheck.warning", "False").lower() == "true"
        _check_spark_version(sc, report_warn)


def _split_full_version(version):
    parts = version.split(".")
    major = parts[0]
    feature = parts[1]
    maintenance = parts[2]
    return (major, feature, maintenance)


def _check_spark_version(sc, report_warn):
    version_info = _get_bigdl_verion_conf()
    (c_major, c_feature, c_maintenance) = _split_full_version(version_info['spark_version'])
    (r_major, r_feature, r_maintenance) = _split_full_version(sc.version)
    error_message = \
        """
        The compile time spark version is not compatible with the spark runtime version.
        Compile time version is %s, runtime version is %s. If you want bypass this check,
        please set spark.analytics.zoo.versionCheck to false, and if you want to only report
        an warning message, please set spark.analytics.zoo.versionCheck.warning to true.
        """ % (version_info['spark_version'], sc.version)
    if c_major != r_major:
        if not report_warn:
            print("***************************Usage Error*****************************")
            print(error_message)
            raise RuntimeError(error_message)
        else:
            warnings.warn(error_message)
    elif not (c_maintenance == r_maintenance and c_feature == r_feature):
        warnings.warn("The compile time spark version may not compatible with " +
                      "the Spark runtime version. " +
                      "Compile time version is %s, " % version_info['spark_version'] +
                      "runtime version is %s" % sc.version)


def _get_bigdl_verion_conf():
    bigdl_build_file = "zoo-version-info.properties"
    bigdl_python_wrapper = "python-api.zip"
    """Saves the Trainer state to the provided checkpoint path.

    Args:
        checkpoint (str): Path to target checkpoint file.
    """

    for p in sys.path:
        if bigdl_build_file in p and os.path.isfile(p):
            with open(p) if sys.version_info < (3,) else open(p, encoding='latin-1') as conf_file:
                return load_conf(conf_file.read(), "=")
        if bigdl_python_wrapper in p and os.path.isfile(p):
            import zipfile
            with zipfile.ZipFile(p, 'r') as zip_conf:
                if bigdl_build_file in zip_conf.namelist():
                    content = zip_conf.read(bigdl_build_file)
                    if sys.version_info >= (3,):
                        content = str(content, 'latin-1')
                    return load_conf(content, "=")
    raise RuntimeError("Error while locating file zoo-version-info.properties, " +
                       "please make sure the mvn generate-resources phase" +
                       " is executed and a zoo-version-info.properties file" +
                       " is located in zoo/target/extra-resources")


def load_conf(conf_str, split_char=None):
    """Saves the Trainer state to the provided checkpoint path.

    Args:
        checkpoint (str): Path to target checkpoint file.
    """

    return dict(line.split(split_char) for line in conf_str.split("\n") if
                "#" not in line and line.strip())


def set_optimizer_version(optimizerVersion, bigdl_type="float"):
    """
    Set DistriOptimizer version.
    param optimizerVersion: should be "OptimizerV1" or "OptimizerV2".
    """
    callZooFunc(bigdl_type, "setOptimizerVersion", optimizerVersion)


def get_optimizer_version(bigdl_type="float"):
    """
    Get DistriOptimizer version.
    return optimizerVersion
    """
    return callZooFunc(bigdl_type, "getOptimizerVersion")
