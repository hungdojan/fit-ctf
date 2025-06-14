import fit_ctf_components.container_client.container_client_interface as c_client
import fit_ctf_components.container_client.docker_client as docker_client
import fit_ctf_components.container_client.mock_client as mock_client
import fit_ctf_components.container_client.podman_client as podman_client


def get_c_client_by_name(name: str) -> type[c_client.ContainerClientInterface]:
    """Choose the container client wrapper.

    :param name: A name of the container engine/
    :type name: str
    :raises ValueError: When unsupported container engine was given.
    :return: A `ContainerClientInterface` based class.
    :rtype: type[ContainerClientInterface]
    """
    if name == "podman":
        return podman_client.PodmanClient
    elif name == "mock":
        return mock_client.MockClient
    elif name == "docker":
        return docker_client.DockerClient
    else:  # pragma: no cover
        raise ValueError("Given container engine name is not supported.")
