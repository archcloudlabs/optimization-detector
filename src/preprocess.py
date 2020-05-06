import itertools
import math
import os
import random
from typing import List

from .binaryds import BinaryDs


def run_preprocess(input_dir: str, category: int, model_dir: str,
                   function: bool, features: int, split: float) -> None:
    """
    Perform the preprocessing by adding a category and writes (or updates) the
    binary file containing the dataset on disk

    Parameters
    ---------
    input_dir: str
        The folder where the examples for a single category can be found
    category: int
        The id of the category that will be written
    model_dir: str
        Path to the folder where the train.bin and test.bin can be found (
        or will be created)
    function: bool
        True if this method has a function level granularity
    features: int
        How many features (i.e. The number of bytes for each example)
    split: float
        The ratio training examples over total examples
    """
    train = BinaryDs(os.path.join(model_dir, "train.bin"))
    test = BinaryDs(os.path.join(model_dir, "test.bin"))
    files = gather_files(input_dir, function)
    read_dataset(train, function, features)
    read_dataset(test, function, features)
    data = read_and_clean_content(files, function)
    random.shuffle(data)
    split_index = math.floor(len(data) * split)
    new_train_data = data[:split_index]
    new_test_data = data[split_index:]
    # most times this will return just []
    current_train_data = train.get(category)
    current_test_data = test.get(category)
    current_train_data.extend(new_train_data)
    current_test_data.extend(new_test_data)
    train.set(category, current_train_data)
    test.set(category, current_test_data)
    train.rebalance(test)


def read_dataset(dataset: BinaryDs, function: bool, features: int) -> None:
    """
    Read the dataset and assert that is compatible with the requested
    granularity and features.

    Parameters
    ---------
    dataset: BinaryDs
        The dataset that will be read
    function: bool
        If function granularity has been requested
    features: int
        Number of features requested
    """
    try:
        dataset.read()
        # validate dataset
        if dataset.get_function_granularity() != function:
            raise ValueError("Incompatible granularity between existing "
                             "dataset and requested changes")
        if dataset.get_features() != features:
            raise ValueError("Incompatible number of features between "
                             "existing dataset and requested changes")
    except FileNotFoundError:
        # setup dataset
        dataset.set_features(features)
        dataset.set_function_granularity(function)


def read_and_clean_content(files: List[str], function: bool,
                           features: int) -> List[bytes]:
    """
    Read the raw files provided by the other program and merge all
    functions of the various files

    Parameters
    ---------
    files: List[str]
        List of paths to every file that will be processed
    function: bool
        True if the requested analysis should be function grained
    features: int
        The number of features expected

    Returns
    -------
    List[bytes]: A list of bytes where each element is an example in the
                 category
    """
    if function:
        x = read_files_function(files)
        x = encode_opcodes(x)
    else:
        x = read_files_raw(files)
        # split in chunks of "features" length
        x = [x[i:i + features] for i in range(0, len(x), features)]
        # flatten
        x = list(itertools.chain.from_iterable(x))
    return x


def encode_opcodes(func_list: List[str]) -> List[bytes]:
    """
    Transform a comma separated list of opcodes (as string bytes) into a
    list of bytes

    Parameters
    ---------
    func_list: List[str]
        The list of opcodes in the form ["DE,AD,C0,DE,01"]. No spaces or
        single digits allowed (i.e. write 01 instead of 1).

    Returns
    -------
    List[bytes]: A list of bytes where each element is an example in the
                 category
    """
    func_list = list(map(lambda x: x.replace(",", ""), func_list))
    func_list = list(map(bytes.fromhex, func_list))
    return func_list


def gather_files(path: str, function: bool) -> List[str]:
    """
    Find all files contained in a directory and filter them based on their
    extensions

    Parameters
    ----------
    path: str
        Path to the folder containing the files
    function: bool
        True if function grained is requested (will parse .txt files,
        .bin otherwise)

    Returns
    -------
    List[str]: A list of paths to every file contained in the folder with .txt
                or .bin extension (based on the function parameter)
    """
    files = list()
    for _, _, files in os.walk(path):
        for cur_file in files:
            cur_abs = os.path.join(path, cur_file)
            files.append(cur_abs)
    if function:
        ext = ".txt"
    else:
        ext = ".bin"
    files = list(filter(lambda x: os.path.splitext(x)[1] == ext, files))
    if len(files) == 0:
        raise FileNotFoundError(f"No files with the correct extension, "
                                "{ext} were found in the given folder")
    return files


def read_files_function(files_list: List[str]) -> List[str]:
    """
    Read all the function opcodes contained in a file. Every line of the file
    is expected to contain the opcodes.

    Parameters
    ----------
    files_list: List[str]
        The list of files that will be parsed

    Returns
    ------
    List[str]: A list of every sample contained in the file, where each
              sample is a string in the form "DE,AD,C0,DE"
    """
    functions = list()
    for cur_file in files_list:
        with open(cur_file, 'r') as f:
            for cnt, line in enumerate(f):
                line = line.strip('\n')
                if line == "FF," or line == "" or line == "[]":
                    continue
                functions.append(line)
    return functions


def read_files_raw(files_list: List[str]) -> List[bytes]:
    """
    Read all the raw bytes contained in a file.

    Parameters
    ----------
    files_list: List[str]
        The list of files that will be parsed

    Returns
    ------
    List[bytes]: A list of every sample contained in the file, where each
              sample is a sequence of bytes
    """
    functions = list()
    for cur_file in files_list:
        with open(cur_file, 'rb') as f:
            functions.append(f.read())
    return functions
