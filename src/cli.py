"""Command-line interface for Tintri OpenTelemetry Receiver."""

import argparse
import logging
import signal
import sys
from typing import Optional

from tintri_receiver.config import TintriReceiverConfig
from tintri_receiver.receiver import TintriReceiver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ReceiverCLI:
    """Command-line interface for Tintri receiver."""
    
    def __init__(self):
        """Initialize CLI."""
        self.receiver: Optional[TintriReceiver] = None
        self.running = False
    
    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown()
    
    def run(self, config_path: str, log_level: str = "INFO") -> int:
        """Run the receiver.
        
        Args:
            config_path: Path to configuration file
            log_level: Logging level
            
        Returns:
            Exit code (0 for success)
        """
        # Set log level
        logging.getLogger().setLevel(getattr(logging, log_level.upper()))
        
        try:
            # Load configuration
            logger.info(f"Loading configuration from {config_path}")
            config = TintriReceiverConfig.from_yaml(config_path)
            
            # Create receiver
            logger.info("Initializing Tintri receiver...")
            self.receiver = TintriReceiver(config)
            
            # Setup signal handlers
            self.setup_signal_handlers()
            
            # Start receiver
            self.receiver.start()
            self.running = True
            
            logger.info("Receiver is running. Press Ctrl+C to stop.")
            
            # Keep running until stopped
            signal.pause()
            
            return 0
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            return 0
        except Exception as e:
            logger.error(f"Error running receiver: {e}", exc_info=True)
            return 1
        finally:
            self.shutdown()
    
    def shutdown(self) -> None:
        """Shutdown the receiver gracefully."""
        if self.running and self.receiver:
            logger.info("Shutting down receiver...")
            try:
                self.receiver.stop()
                self.running = False
                logger.info("Receiver shutdown complete")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")


def main() -> int:
    """Main entry point for CLI.
    
    Returns:
        Exit code
    """
    parser = argparse.ArgumentParser(
        description="Tintri OpenTelemetry Receiver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with config file
  tintri-receiver --config config.yaml
  
  # Run with debug logging
  tintri-receiver --config config.yaml --log-level DEBUG
  
  # Validate configuration only
  tintri-receiver --config config.yaml --validate
        """,
    )
    
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to configuration file (YAML)",
    )
    
    parser.add_argument(
        "--log-level",
        "-l",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate configuration and exit",
    )
    
    args = parser.parse_args()
    
    # Validate configuration only
    if args.validate:
        try:
            config = TintriReceiverConfig.from_yaml(args.config)
            config.validate()
            print(f"✓ Configuration is valid")
            print(f"  - TGC configured: {'Yes' if config.tgc else 'No'}")
            print(f"  - VMstores configured: {len(config.vmstores)}")
            return 0
        except Exception as e:
            print(f"✗ Configuration validation failed: {e}")
            return 1
    
    # Run receiver
    cli = ReceiverCLI()
    return cli.run(args.config, args.log_level)


if __name__ == "__main__":
    sys.exit(main())
