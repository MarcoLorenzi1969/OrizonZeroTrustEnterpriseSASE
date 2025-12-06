"""
Orizon Zero Trust Connect - GeoLocation Service
Local IP geolocation using MaxMind GeoLite2 databases
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger

try:
    import geoip2.database
    import geoip2.errors
    GEOIP2_AVAILABLE = True
except ImportError:
    GEOIP2_AVAILABLE = False
    logger.warning("geoip2 library not installed. Geolocation will use fallback.")


@dataclass
class GeoLocation:
    """Geolocation result data class"""
    ip: str
    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    region_code: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    accuracy_radius: Optional[int] = None  # in km
    # ASN info
    asn: Optional[int] = None
    asn_org: Optional[str] = None
    isp: Optional[str] = None
    # Source info
    source: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ip": self.ip,
            "country": self.country,
            "countryCode": self.country_code,
            "region": self.region,
            "regionCode": self.region_code,
            "city": self.city,
            "zip": self.postal_code,
            "lat": self.latitude,
            "lon": self.longitude,
            "timezone": self.timezone,
            "accuracy_radius_km": self.accuracy_radius,
            "asn": self.asn,
            "org": self.asn_org,
            "isp": self.isp or self.asn_org,
            "source": self.source,
            "status": "success" if self.latitude else "fail"
        }


class GeoLocationService:
    """
    GeoLocation service using local MaxMind GeoLite2 databases.

    Provides fast, offline IP geolocation lookups without API rate limits.
    """

    _instance = None
    _city_reader = None
    _asn_reader = None

    # Default paths for GeoLite2 databases
    DEFAULT_DATA_DIR = "/app/data/geoip"
    CITY_DB = "GeoLite2-City.mmdb"
    ASN_DB = "GeoLite2-ASN.mmdb"

    def __new__(cls):
        """Singleton pattern for database readers"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._init_readers()

    def _init_readers(self):
        """Initialize GeoIP2 database readers"""
        if not GEOIP2_AVAILABLE:
            logger.error("geoip2 library not available")
            return

        data_dir = os.getenv("GEOIP_DATA_DIR", self.DEFAULT_DATA_DIR)

        # Try to load City database
        city_path = os.path.join(data_dir, self.CITY_DB)
        if os.path.exists(city_path):
            try:
                self._city_reader = geoip2.database.Reader(city_path)
                logger.info(f"Loaded GeoLite2-City database from {city_path}")
            except Exception as e:
                logger.error(f"Failed to load City database: {e}")
        else:
            logger.warning(f"City database not found at {city_path}")

        # Try to load ASN database
        asn_path = os.path.join(data_dir, self.ASN_DB)
        if os.path.exists(asn_path):
            try:
                self._asn_reader = geoip2.database.Reader(asn_path)
                logger.info(f"Loaded GeoLite2-ASN database from {asn_path}")
            except Exception as e:
                logger.error(f"Failed to load ASN database: {e}")
        else:
            logger.warning(f"ASN database not found at {asn_path}")

    def is_available(self) -> bool:
        """Check if geolocation service is available"""
        return self._city_reader is not None

    def lookup(self, ip_address: str) -> GeoLocation:
        """
        Look up geolocation for an IP address.

        Args:
            ip_address: IPv4 or IPv6 address

        Returns:
            GeoLocation object with location data
        """
        result = GeoLocation(ip=ip_address, source="geolite2")

        # Skip private/reserved IPs
        if self._is_private_ip(ip_address):
            result.source = "private_ip"
            logger.debug(f"Skipping private IP: {ip_address}")
            return result

        # City lookup
        if self._city_reader:
            try:
                city_response = self._city_reader.city(ip_address)

                # Country info
                if city_response.country:
                    result.country = city_response.country.name
                    result.country_code = city_response.country.iso_code

                # Region/subdivision info
                if city_response.subdivisions:
                    subdivision = city_response.subdivisions.most_specific
                    result.region = subdivision.name
                    result.region_code = subdivision.iso_code

                # City info
                if city_response.city:
                    result.city = city_response.city.name

                # Postal code
                if city_response.postal:
                    result.postal_code = city_response.postal.code

                # Coordinates
                if city_response.location:
                    result.latitude = city_response.location.latitude
                    result.longitude = city_response.location.longitude
                    result.timezone = city_response.location.time_zone
                    result.accuracy_radius = city_response.location.accuracy_radius

            except geoip2.errors.AddressNotFoundError:
                logger.debug(f"IP not found in City database: {ip_address}")
            except Exception as e:
                logger.error(f"City lookup error for {ip_address}: {e}")

        # ASN lookup
        if self._asn_reader:
            try:
                asn_response = self._asn_reader.asn(ip_address)
                result.asn = asn_response.autonomous_system_number
                result.asn_org = asn_response.autonomous_system_organization
                result.isp = asn_response.autonomous_system_organization
            except geoip2.errors.AddressNotFoundError:
                pass
            except Exception as e:
                logger.error(f"ASN lookup error for {ip_address}: {e}")

        return result

    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is private/reserved"""
        import ipaddress
        try:
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved
        except ValueError:
            return False

    def close(self):
        """Close database readers"""
        if self._city_reader:
            self._city_reader.close()
            self._city_reader = None
        if self._asn_reader:
            self._asn_reader.close()
            self._asn_reader = None
        self._initialized = False


# Global singleton instance
_geo_service: Optional[GeoLocationService] = None


def get_geolocation_service() -> GeoLocationService:
    """Get the global GeoLocationService instance"""
    global _geo_service
    if _geo_service is None:
        _geo_service = GeoLocationService()
    return _geo_service


def lookup_ip(ip_address: str) -> Dict[str, Any]:
    """
    Convenience function to lookup an IP address.

    Args:
        ip_address: IPv4 or IPv6 address

    Returns:
        Dictionary with geolocation data
    """
    service = get_geolocation_service()
    result = service.lookup(ip_address)
    return result.to_dict()
