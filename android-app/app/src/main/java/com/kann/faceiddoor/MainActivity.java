package com.kann.faceiddoor;

import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public class MainActivity extends AppCompatActivity {
    private SessionManager sessionManager;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        sessionManager = new SessionManager(this);
        TextView doorStatus = findViewById(R.id.doorStatus);
        TextView actionResult = findViewById(R.id.actionResult);

        Button refreshBtn = findViewById(R.id.refreshStatusButton);
        Button unlockBtn = findViewById(R.id.unlockButton);
        Button guestsBtn = findViewById(R.id.guestsButton);
        Button inviteBtn = findViewById(R.id.inviteButton);
        Button notificationsBtn = findViewById(R.id.notificationsButton);

        refreshBtn.setOnClickListener(v -> loadDoorStatus(doorStatus));
        unlockBtn.setOnClickListener(v -> unlockDoor(actionResult, doorStatus));
        guestsBtn.setOnClickListener(v -> startActivity(new Intent(this, GuestManagementActivity.class)));
        inviteBtn.setOnClickListener(v -> startActivity(new Intent(this, InviteLinkActivity.class)));
        notificationsBtn.setOnClickListener(v -> startActivity(new Intent(this, NotificationsActivity.class)));

        loadDoorStatus(doorStatus);
    }

    private void loadDoorStatus(TextView target) {
        new Thread(() -> {
            try {
                String body = ApiClient.get("/door/status", sessionManager.getToken());
                JsonObject obj = JsonParser.parseString(body).getAsJsonObject();
                boolean unlocked = obj.get("is_unlocked").getAsBoolean();
                runOnUiThread(() -> target.setText(unlocked ? "Door: UNLOCKED" : "Door: LOCKED"));
            } catch (Exception e) {
                runOnUiThread(() -> target.setText("Door: unavailable"));
            }
        }).start();
    }

    private void unlockDoor(TextView result, TextView status) {
        new Thread(() -> {
            try {
                ApiClient.postJson("/door/unlock", "{}", sessionManager.getToken());
                runOnUiThread(() -> {
                    result.setText("Door unlocked for 5 seconds.");
                    status.setText("Door: UNLOCKED");
                });
            } catch (Exception e) {
                runOnUiThread(() -> result.setText("Unlock failed"));
            }
        }).start();
    }
}
