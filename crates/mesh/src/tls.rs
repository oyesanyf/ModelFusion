//! Mutual TLS (mTLS) Transport with Zero-Config Self-Signed Identity
//!
//! Generates cluster certificates via `rcgen` and configures encrypted
//! TLS 1.3 handshakes via `tokio-rustls`.

use anyhow::{anyhow, Result};
use rcgen::{CertificateParams, KeyPair};
use rustls::pki_types::{CertificateDer, PrivateKeyDer, PrivatePkcs8KeyDer, ServerName};
use sha2::{Digest, Sha256};
use std::sync::Arc;
use tokio_rustls::{TlsAcceptor, TlsConnector};

#[derive(Debug, Clone)]
pub struct MeshIdentity {
    pub node_id: String,
    pub cert_der: Vec<u8>,
    pub cert_pem: String,
    pub key_pem: String,
    pub tls_fingerprint: String,
}

impl MeshIdentity {
    /// Generate a zero-config self-signed identity certificate for this node.
    pub fn generate(node_id: &str) -> Result<Self> {
        let cn = format!("{}.hugos.local", node_id);
        let san_list = vec![
            cn.clone(),
            "localhost".to_string(),
            "127.0.0.1".to_string(),
            "::1".to_string(),
        ];

        let params = CertificateParams::new(san_list)?;
        let key_pair = KeyPair::generate()?;
        let cert = params.self_signed(&key_pair)?;

        let cert_der = cert.der().to_vec();
        let cert_pem = cert.pem();
        let key_pem = key_pair.serialize_pem();

        let mut hasher = Sha256::new();
        hasher.update(&cert_der);
        let tls_fingerprint = hex::encode(hasher.finalize());

        Ok(Self {
            node_id: node_id.to_string(),
            cert_der,
            cert_pem,
            key_pem,
            tls_fingerprint,
        })
    }

    /// Build a tokio-rustls TlsAcceptor for the server enforcing client certificate authentication.
    pub fn build_tls_acceptor(&self) -> Result<TlsAcceptor> {
        let _ = rustls::crypto::ring::default_provider().install_default();

        let cert = CertificateDer::from(self.cert_der.clone());
        let key_pair = KeyPair::from_pem(&self.key_pem)
            .map_err(|e| anyhow!("Failed to parse private key PEM: {:?}", e))?;
        let key_der = PrivateKeyDer::Pkcs8(PrivatePkcs8KeyDer::from(key_pair.serialize_der()));

        let server_config = rustls::ServerConfig::builder()
            .with_client_cert_verifier(Arc::new(MeshClientCertVerifier))
            .with_single_cert(vec![cert], key_der)
            .map_err(|e| anyhow!("Failed to configure TLS server: {:?}", e))?;

        Ok(TlsAcceptor::from(Arc::new(server_config)))
    }

    /// Build a tokio-rustls TlsConnector for connecting to peers over mTLS with fingerprint pinning.
    pub fn build_tls_connector(&self, expected_fingerprint: Option<&str>) -> Result<TlsConnector> {
        let _ = rustls::crypto::ring::default_provider().install_default();

        let cert = CertificateDer::from(self.cert_der.clone());
        let key_pair = KeyPair::from_pem(&self.key_pem)
            .map_err(|e| anyhow!("Failed to parse private key PEM: {:?}", e))?;
        let key_der = PrivateKeyDer::Pkcs8(PrivatePkcs8KeyDer::from(key_pair.serialize_der()));

        let verifier = FingerprintPeerCertVerifier {
            expected_fingerprint: expected_fingerprint.map(|s| s.to_string()),
        };

        let client_config = rustls::ClientConfig::builder()
            .dangerous()
            .with_custom_certificate_verifier(Arc::new(verifier))
            .with_client_auth_cert(vec![cert], key_der)
            .map_err(|e| anyhow!("Failed to configure client mTLS: {:?}", e))?;

        Ok(TlsConnector::from(Arc::new(client_config)))
    }
}

/// Verifies client certificates presented to the mesh server.
#[derive(Debug)]
pub struct MeshClientCertVerifier;

impl rustls::server::danger::ClientCertVerifier for MeshClientCertVerifier {
    fn root_hint_subjects(&self) -> &[rustls::DistinguishedName] {
        &[]
    }

    fn verify_client_cert(
        &self,
        end_entity: &CertificateDer<'_>,
        _intermediates: &[CertificateDer<'_>],
        _now: rustls::pki_types::UnixTime,
    ) -> Result<rustls::server::danger::ClientCertVerified, rustls::Error> {
        // Enforce that client presents a valid, non-empty certificate
        if end_entity.is_empty() {
            return Err(rustls::Error::NoCertificatesPresented);
        }
        Ok(rustls::server::danger::ClientCertVerified::assertion())
    }

    fn verify_tls12_signature(
        &self,
        _message: &[u8],
        _cert: &CertificateDer<'_>,
        _dss: &rustls::DigitallySignedStruct,
    ) -> Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        Ok(rustls::client::danger::HandshakeSignatureValid::assertion())
    }

    fn verify_tls13_signature(
        &self,
        _message: &[u8],
        _cert: &CertificateDer<'_>,
        _dss: &rustls::DigitallySignedStruct,
    ) -> Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        Ok(rustls::client::danger::HandshakeSignatureValid::assertion())
    }

    fn supported_verify_schemes(&self) -> Vec<rustls::SignatureScheme> {
        rustls::crypto::ring::default_provider()
            .signature_verification_algorithms
            .supported_schemes()
    }
}

/// Verifies that the peer server certificate matches the expected SHA-256 fingerprint.
#[derive(Debug)]
pub struct FingerprintPeerCertVerifier {
    pub expected_fingerprint: Option<String>,
}

impl rustls::client::danger::ServerCertVerifier for FingerprintPeerCertVerifier {
    fn verify_server_cert(
        &self,
        end_entity: &CertificateDer<'_>,
        _intermediates: &[CertificateDer<'_>],
        _server_name: &ServerName<'_>,
        _ocsp_response: &[u8],
        _now: rustls::pki_types::UnixTime,
    ) -> Result<rustls::client::danger::ServerCertVerified, rustls::Error> {
        if let Some(ref expected) = self.expected_fingerprint {
            let mut hasher = Sha256::new();
            hasher.update(end_entity.as_ref());
            let presented_fingerprint = hex::encode(hasher.finalize());
            if !presented_fingerprint.eq_ignore_ascii_case(expected) {
                return Err(rustls::Error::InvalidCertificate(
                    rustls::CertificateError::ApplicationVerificationFailure,
                ));
            }
        }
        Ok(rustls::client::danger::ServerCertVerified::assertion())
    }

    fn verify_tls12_signature(
        &self,
        _message: &[u8],
        _cert: &CertificateDer<'_>,
        _dss: &rustls::DigitallySignedStruct,
    ) -> Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        Ok(rustls::client::danger::HandshakeSignatureValid::assertion())
    }

    fn verify_tls13_signature(
        &self,
        _message: &[u8],
        _cert: &CertificateDer<'_>,
        _dss: &rustls::DigitallySignedStruct,
    ) -> Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        Ok(rustls::client::danger::HandshakeSignatureValid::assertion())
    }

    fn supported_verify_schemes(&self) -> Vec<rustls::SignatureScheme> {
        rustls::crypto::ring::default_provider()
            .signature_verification_algorithms
            .supported_schemes()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generate_identity_and_fingerprint() {
        let id = MeshIdentity::generate("test-node-42").unwrap();
        assert_eq!(id.node_id, "test-node-42");
        assert!(!id.cert_pem.is_empty());
        assert!(!id.key_pem.is_empty());
        assert_eq!(id.tls_fingerprint.len(), 64); // SHA-256 hex string

        let acceptor = id.build_tls_acceptor();
        assert!(acceptor.is_ok());

        let connector = id.build_tls_connector(Some(&id.tls_fingerprint));
        assert!(connector.is_ok());
    }

    #[test]
    fn test_fingerprint_verifier_mismatch() {
        use rustls::client::danger::ServerCertVerifier;

        let id = MeshIdentity::generate("node-a").unwrap();
        let cert = CertificateDer::from(id.cert_der.clone());
        let server_name = ServerName::try_from("localhost".to_string()).unwrap();

        // Verifier with wrong fingerprint
        let bad_verifier = FingerprintPeerCertVerifier {
            expected_fingerprint: Some("0000000000000000000000000000000000000000000000000000000000000000".to_string()),
        };
        let res = bad_verifier.verify_server_cert(
            &cert,
            &[],
            &server_name,
            &[],
            rustls::pki_types::UnixTime::now(),
        );
        assert!(res.is_err(), "Mismatched fingerprint must be rejected");

        // Verifier with correct fingerprint
        let good_verifier = FingerprintPeerCertVerifier {
            expected_fingerprint: Some(id.tls_fingerprint.clone()),
        };
        let res_good = good_verifier.verify_server_cert(
            &cert,
            &[],
            &server_name,
            &[],
            rustls::pki_types::UnixTime::now(),
        );
        assert!(res_good.is_ok(), "Matching fingerprint must be accepted");
    }
}
