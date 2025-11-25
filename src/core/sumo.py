import traci
import threading
import time

from typing import Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

from ..utils.config import Config
from ..utils import logger


class ConnectionState(Enum):
    """SUMO connection states."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class SumoConfigOptions:
    """SUMO simulation configuration."""

    sumo_binary: str
    config_file: str
    port: int
    num_clients: int
    gui: bool
    step_length: float
    auto_start: bool
    auto_reconnect: bool
    max_reconnect_attempts: int
    reconnect_delay: float


class Sumo:
    """
    SUMO TraCI connection manager.

    Handles connection lifecycle, error recovery, and provides
    a high-level interface for SUMO operations.
    """

    def __init__(
        self, options: Optional[SumoConfigOptions] = {}, configMgr: Config = Config()
    ):
        """
        Initialize SUMO connector.

        Args:
            config: SUMO configuration parameters
            logger_config: Logger configuration
        """
        config = configMgr.get_section("simulation")
        self.config = {**options, **config}
        self.logger = logger.new_logger({"name": "sumo_connector"}, configMgr)

        self._connection_state = ConnectionState.DISCONNECTED
        self._connection_lock = threading.RLock()
        self._simulation_step = 0
        self._is_running = False
        self._reconnect_count = 0

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._connection_state

    @property
    def is_connected(self) -> bool:
        """Check if connected to SUMO."""
        return self._connection_state == ConnectionState.CONNECTED

    @property
    def simulation_step(self) -> int:
        """Get current simulation step."""
        return self._simulation_step

    def connect(self) -> bool:
        """
        Establish connection to SUMO.

        Returns:
            True if connection successful, False otherwise
        """
        with self._connection_lock:
            if self._connection_state == ConnectionState.CONNECTED:
                self.logger.warning("Already connected to SUMO")
                return True

            self._connection_state = ConnectionState.CONNECTING
            self.logger.info(f"Connecting to SUMO on port {self.config['port']}")

            try:
                sumo_binary = (
                    "sumo-gui" if self.config["gui"] else self.config["sumo_binary"]
                )

                sumo_cmd = [
                    sumo_binary,
                    "-c",
                    self.config["config_file"],
                    "--start",
                    "--delay",
                    str(self.config["delay"]),
                ]

                traci.start(sumo_cmd)

                self._connection_state = ConnectionState.CONNECTED
                self._simulation_step = 0
                self._is_running = True
                self._reconnect_count = 0

                self.logger.info("Successfully connected to SUMO")
                return True
            except Exception as e:
                self._connection_state = ConnectionState.ERROR
                self.logger.error(f"Failed to connect to SUMO: {e}")
                return False

    def disconnect(self) -> None:
        """Disconnect from SUMO."""
        with self._connection_lock:
            if self._connection_state == ConnectionState.DISCONNECTED:
                return

            self.logger.info("Disconnecting from SUMO")

            try:
                if self._connection_state == ConnectionState.CONNECTED:
                    traci.close()

                self._connection_state = ConnectionState.DISCONNECTED
                self._is_running = False

                self.logger.info("Disconnected from SUMO")
            except Exception as e:
                self.logger.error(f"Error during disconnect: {e}")
                self._connection_state = ConnectionState.ERROR

    def step(self) -> bool:
        """
        Execute one simulation step.

        Returns:
            True if step successful, False otherwise
        """
        if not self.is_connected:
            return False

        try:
            traci.simulationStep()
            self._simulation_step += 1
            return True

        except Exception as e:
            self.logger.error(f"Simulation step failed: {e}")
            self._handle_connection_error(e)
            return False

    def run_simulation(
        self,
        duration: Optional[int] = None,
        step_callback: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """
        Run simulation for specified duration.

        Args:
            duration: Simulation duration in steps (None = run until end)
            step_callback: Optional callback for each step

        Returns:
            True if simulation completed successfully
        """
        if not self.is_connected:
            self.logger.error("Cannot run simulation - not connected to SUMO")
            return False

        self.logger.info(f"Starting simulation for {duration or 'unlimited'} steps")

        try:
            step_count = 0
            while self._is_running and (duration is None or step_count < duration):
                if not self.step():
                    break

                if step_callback:
                    step_callback(self._simulation_step)

                # Check if simulation has ended
                if traci.simulation.getMinExpectedNumber() <= 0:
                    self.logger.info("Simulation completed - no more vehicles")
                    break

                step_count += 1

            self.logger.info(f"Simulation finished after {step_count} steps")
            return True

        except Exception as e:
            self.logger.error(f"Simulation run failed: {e}")
            self._handle_connection_error(e)
            return False

    def reset_simulation(self) -> bool:
        """
        Reset simulation to initial state.

        Returns:
            True if reset successful
        """
        self.logger.info("Resetting simulation")

        try:
            # Disconnect and reconnect to reset state
            self.disconnect()
            time.sleep(0.5)

            if self.connect():
                self.logger.info("Simulation reset completed")
                return True
            else:
                self.logger.error("Failed to reconnect after reset")
                return False

        except Exception as e:
            self.logger.error(f"Simulation reset failed: {e}")
            return False

    def _verify_connection(self) -> bool:
        """Verify SUMO connection is working."""
        try:
            traci.simulation.getVersion()
            traci.simulation.getCurrentTime()
            return True
        except Exception:
            return False

    def _handle_connection_error(self, error: Exception) -> None:
        """Handle connection errors with auto-reconnect if enabled."""
        self.logger.warning(f"Connection error detected: {error}")

        if (
            self.config["auto_reconnect"]
            and self._reconnect_count < self.config["max_reconnect_attempts"]
        ):
            self._attempt_reconnect()
        else:
            self._connection_state = ConnectionState.ERROR
            self._trigger_callbacks(self._on_error_callbacks, error)

    def _attempt_reconnect(self) -> None:
        """Attempt to reconnect to SUMO."""
        self._reconnect_count += 1
        self._connection_state = ConnectionState.RECONNECTING

        self.logger.info(
            f"Attempting reconnection {self._reconnect_count}/{self.config['max_reconnect_attempts']}"
        )

        time.sleep(self.config["reconnect_delay"])

        try:
            self.disconnect()
            time.sleep(0.5)

            if self.connect():
                self.logger.info("Reconnection successful")
            else:
                self.logger.error("Reconnection failed")

        except Exception as e:
            self.logger.error(f"Reconnection attempt failed: {e}")
            if self._reconnect_count >= self.config["max_reconnect_attempts"]:
                self._connection_state = ConnectionState.ERROR

    def _trigger_callbacks(self, callbacks: List[Callable], *args) -> None:
        """Trigger event callbacks safely."""
        for callback in callbacks:
            try:
                callback(*args)
            except Exception as e:
                self.logger.error(f"Callback error: {e}")
