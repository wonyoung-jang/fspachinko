"""Tests for filenamer.py."""


# def test_get_filenamer_fn() -> None:
#     """Test get_filenamer_fn."""
#     filenamer = get_filenamer_fn(template=" ", is_enabled=False)
#     assert isinstance(filenamer, Callable)
#     filenamer = get_filenamer_fn(template=FilenameTemplate.ORIGINAL, is_enabled=True)
#     assert isinstance(filenamer, Callable)
#     filenamer = get_filenamer_fn(template="{original}_{index}", is_enabled=True)
#     assert isinstance(filenamer, Callable)


# def test_get_dirname_fn() -> None:
#     """Test get_dirname_fn."""
#     dirname_fn = get_dirname_fn(dest="dest", name="", is_enabled=False)
#     assert isinstance(dirname_fn, Callable)
#     assert dirname_fn() == "dest"
#     dirname_fn = get_dirname_fn(dest="dest", name="test", is_enabled=True)
#     assert isinstance(dirname_fn, Callable)
#     assert dirname_fn() == os.path.join("dest", "test")


# def test_get_filecount_fn() -> None:
#     """Test get_filecount_fn."""
#     filecount_fn = get_filecount_fn(count=5, rand_min=1, rand_max=10, is_rand_enabled=False)
#     assert isinstance(filecount_fn, Callable)
#     assert filecount_fn() == 5
#     filecount_fn = get_filecount_fn(count=5, rand_min=1, rand_max=10, is_rand_enabled=True)
#     assert isinstance(filecount_fn, Callable)
#     assert 1 <= filecount_fn() <= 10


# def test_get_transfer_fn() -> None:
#     """Test get_transfer_fn."""
#     for mode in TransferMode:
#         transfer_fn = get_transfer_fn(mode.value)
#         assert transfer_fn is not None
#         assert isinstance(transfer_fn, Callable)


# def test_get_text_filter_fn() -> None:
#     """Test get_text_filter_fn."""
#     text_filter_fn = get_textfilter_fn(text="", re_fmt=r"test", is_enabled=True, should_include=True)
#     assert text_filter_fn is None
#     text_filter_fn = get_textfilter_fn(text="test", re_fmt=r"test", is_enabled=False, should_include=True)
#     assert text_filter_fn is None
#     text_filter_fn = get_textfilter_fn(text="test", re_fmt=r"test", is_enabled=True, should_include=True)
#     assert isinstance(text_filter_fn, Callable)
#     text_filter_fn = get_textfilter_fn(text="test", re_fmt=r"test", is_enabled=True, should_include=False)
#     assert isinstance(text_filter_fn, Callable)
#     text_filter_fn = get_textfilter_fn(text="test,test2", re_fmt=r"test", is_enabled=True, should_include=True)
#     assert isinstance(text_filter_fn, Callable)
#     text_filter_fn = get_textfilter_fn(text="test,test2", re_fmt=r"test", is_enabled=True, should_include=False)
#     assert isinstance(text_filter_fn, Callable)


# def test_get_rangefilter_fn() -> None:
#     """Test get_rangefilter_fn."""
#     range_filter_fn = get_rangefilter_fn(minimum=0, maximum=100, is_enabled=False)
#     assert range_filter_fn is None
#     range_filter_fn = get_rangefilter_fn(minimum=0, maximum=100, is_enabled=True)
#     assert isinstance(range_filter_fn, Callable)
#     range_filter_fn = get_rangefilter_fn(minimum=-1, maximum=100, is_enabled=True)
#     assert isinstance(range_filter_fn, Callable)
#     range_filter_fn = get_rangefilter_fn(minimum=0, maximum=float("inf"), is_enabled=True)
#     assert isinstance(range_filter_fn, Callable)
#     range_filter_fn = get_rangefilter_fn(minimum=-1, maximum=float("inf"), is_enabled=True)
#     assert range_filter_fn is None


# class FakeCallable:
#     """Fake filter for testing get_filefilter_fn."""

#     def __call__(self, e: Any) -> bool:
#         """Return True."""
#         return True


# def test_get_filefilter_fn() -> None:
#     """Test get_filefilter_fn."""
#     filefilter_fn = get_filefilter_fn(filters=())
#     assert isinstance(filefilter_fn, Callable)
#     filefilter_fn = get_filefilter_fn(filters=(FakeCallable(),))
#     assert isinstance(filefilter_fn, Callable)
#     filefilter_fn = get_filefilter_fn(filters=(FakeCallable(), FakeCallable()))
#     assert isinstance(filefilter_fn, Callable)
