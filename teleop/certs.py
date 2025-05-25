import tempfile
import ipaddress
from pathlib import Path
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_self_signed_cert(ip_address: str):
    # Create temp directory for certs
    temp_dir = Path(tempfile.mkdtemp())
    cert_path = temp_dir / "cert.pem"
    key_path = temp_dir / "key.pem"

    ip = ipaddress.ip_address(ip_address)

    # Generate RSA key pair
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Certificate subject and issuer
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Local Dev Cert"),
        x509.NameAttribute(NameOID.COMMON_NAME, ip_address),
    ])

    # Build certificate
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ip)]),
            critical=False
        )
        .sign(key, hashes.SHA256())
    )

    # Write private key
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption()
        ))

    # Write certificate
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    return str(cert_path), str(key_path)
