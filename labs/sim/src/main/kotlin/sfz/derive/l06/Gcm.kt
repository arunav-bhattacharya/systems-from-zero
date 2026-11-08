package sfz.derive.l06

import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * AES-256 in GCM mode, from the JDK (`javax.crypto`). GCM encrypts and also authenticates: it
 * appends a 16-byte tag, and decryption checks the tag before it returns a single byte. A wrong
 * key, a flipped bit in the ciphertext, or different associated data (aad) all fail the check
 * with `javax.crypto.AEADBadTagException`.
 *
 * The [iv] (12 bytes) must never repeat under the same key.
 */
object Gcm {
    const val TAG_BITS = 128
    const val IV_BYTES = 12

    /** Exercise 1. Encrypt [plaintext] under [key] with "AES/GCM/NoPadding", a [TAG_BITS]-bit tag and [aad]. */
    fun seal(key: SecretKey, iv: ByteArray, plaintext: ByteArray, aad: ByteArray): ByteArray {
        TODO("Cipher.getInstance(\"AES/GCM/NoPadding\"), init for ENCRYPT_MODE with a GCMParameterSpec, updateAAD, doFinal")
    }

    /** Exercise 2. The reverse of [seal]. Throws `AEADBadTagException` if anything doesn't match. */
    fun open(key: SecretKey, iv: ByteArray, sealed: ByteArray, aad: ByteArray): ByteArray {
        TODO("the same cipher in DECRYPT_MODE, the same aad, doFinal")
    }
}
