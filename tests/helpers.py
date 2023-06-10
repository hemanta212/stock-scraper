import pytest


def exception_tester(func, mock_data, exception=tuple()):
    """Helper function to test the get_data method"""
    # Mocking the request method
    mocker, response, *args = mock_data
    mock_request = mocker.patch.object(*args, return_value=response)

    # assert exception
    if exception:
        with pytest.raises(exception):
            func()

    # Assert that the request method was called
    mock_request.assert_called_once()
