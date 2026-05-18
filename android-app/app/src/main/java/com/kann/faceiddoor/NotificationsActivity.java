package com.kann.faceiddoor;

import android.os.Bundle;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.ListView;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.util.ArrayList;

public class NotificationsActivity extends AppCompatActivity {
    private SessionManager sessionManager;
    private final ArrayList<String> rows = new ArrayList<>();
    private ArrayAdapter<String> adapter;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_notifications);

        sessionManager = new SessionManager(this);
        TextView status = findViewById(R.id.notificationsStatus);
        ListView listView = findViewById(R.id.notificationsList);
        Button refresh = findViewById(R.id.refreshNotificationsButton);

        adapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, rows);
        listView.setAdapter(adapter);

        refresh.setOnClickListener(v -> loadNotifications(status));
        loadNotifications(status);
    }

    private void loadNotifications(TextView status) {
        new Thread(() -> {
            try {
                String body = ApiClient.get("/notifications", sessionManager.getToken());
                JsonArray array = JsonParser.parseString(body).getAsJsonArray();
                rows.clear();
                for (JsonElement item : array) {
                    JsonObject obj = item.getAsJsonObject();
                    rows.add(obj.get("created_at").getAsString() + " - " + obj.get("message").getAsString());
                }
                runOnUiThread(() -> {
                    adapter.notifyDataSetChanged();
                    status.setText("Notifications updated");
                });
            } catch (Exception e) {
                runOnUiThread(() -> status.setText("Failed to load notifications"));
            }
        }).start();
    }
}
