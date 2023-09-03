from flask import Flask, request, jsonify, send_file
import boto3
import os
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
import io

app = Flask(__name__)

BUCKET_NAME = 'xyyyy'
AWS_ACCESS_KEY_ID = 'AKIA3MEKFWLK4TI2JYPV'
AWS_SECRET_ACCESS_KEY = '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'
s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

AES_KEY = Fernet.generate_key()
fernet = Fernet(AES_KEY)

user_passwords = {}

user_attempts = {}

def max_attempts_exceeded(user_id):
    if user_id in user_attempts:
        last_attempt_time = user_attempts[user_id]['time']
        if datetime.now() - last_attempt_time <= timedelta(hours=24):
            return user_attempts[user_id]['attempts'] >= 5
        else:
            del user_attempts[user_id]
    return False


@app.route('/encrypt', methods=['POST'])
def encrypt():
    try:
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        image_path = request.files['image']

        if max_attempts_exceeded(user_id):
            return jsonify({'error': 'Maximum attempts exceeded. Try again later.'}), 403

        user_passwords[user_id] = password

        with open(image_path, 'rb') as file:
            data = file.read()
            encrypted_data = fernet.encrypt(data)
        s3.put_object(Bucket=BUCKET_NAME, Key=f'encrypted/{user_id}.png', Body=encrypted_data)

        if user_id in user_attempts:
            del user_attempts[user_id]
        return jsonify({'message': 'Image encrypted successfully.'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/decrypt', methods=['POST'])
def decrypt():
    try:
        user_id = request.form.get('user_id')
        decryption_password = request.form.get('password')

        if max_attempts_exceeded(user_id):
            return jsonify({'error': 'Maximum attempts exceeded. Try again later.'}), 403

        if user_id not in user_passwords or user_passwords[user_id] != decryption_password:
            if user_id in user_attempts:
                user_attempts[user_id]['attempts'] += 1
                user_attempts[user_id]['time'] = datetime.now()
            else:
                user_attempts[user_id] = {'attempts': 1, 'time': datetime.now()}
            return jsonify({'error': 'Invalid password.'}), 401

        encrypted_object = s3.get_object(Bucket=BUCKET_NAME, Key=f'encrypted/{user_id}.png')
        encrypted_data = encrypted_object['Body'].read()
        decrypted_data = fernet.decrypt(encrypted_data)

        return send_file(
            io.BytesIO(decrypted_data),
            mimetype='image/png',
            as_attachment=True,
            download_name=f'decrypted_{user_id}.png'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False)
