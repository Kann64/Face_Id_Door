package com.kann.faceiddoor;

import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public class LoginActivity extends AppCompatActivity {
    private SessionManager sessionManager;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        sessionManager = new SessionManager(this);
        if (sessionManager.isLoggedIn()) {
            startActivity(new Intent(this, MainActivity.class));
            finish();
            return;
        }

        setContentView(R.layout.activity_login);
        EditText emailField = findViewById(R.id.emailField);
        EditText passwordField = findViewById(R.id.passwordField);
        TextView statusText = findViewById(R.id.statusText);
        Button loginButton = findViewById(R.id.loginButton);

        loginButton.setOnClickListener(v -> {
            statusText.setText("Logging in...");
            new Thread(() -> {
                try {
                    String json = "{\"email\":\"" + emailField.getText() + "\",\"password\":\"" + passwordField.getText() + "\"}";
                    String response = ApiClient.postJson("/auth/login", json, null);
                    JsonObject obj = JsonParser.parseString(response).getAsJsonObject();
                    String token = obj.get("access_token").getAsString();
                    sessionManager.saveToken(token);
                    runOnUiThread(() -> {
                        startActivity(new Intent(this, MainActivity.class));
                        finish();
                    });
                } catch (Exception e) {
                    runOnUiThread(() -> statusText.setText("Login failed"));
                }
            }).start();
        });
    }
}
