package com.kann.faceiddoor;

import android.os.Bundle;
import android.content.SharedPreferences;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ListView;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.util.ArrayList;
import java.util.List;

public class GuestManagementActivity extends AppCompatActivity {
    private static final String CACHE_PREFS = "face_id_door_cache";
    private static final String CACHE_GUESTS = "cached_guests_json";
    private SessionManager sessionManager;
    private final List<String> guestIds = new ArrayList<>();
    private final List<String> guestRows = new ArrayList<>();
    private ArrayAdapter<String> adapter;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_guest_management);

        sessionManager = new SessionManager(this);
        EditText guestName = findViewById(R.id.guestNameField);
        TextView status = findViewById(R.id.guestStatus);
        ListView listView = findViewById(R.id.guestListView);
        Button createBtn = findViewById(R.id.createGuestButton);
        Button refreshBtn = findViewById(R.id.refreshGuestButton);
        Button disableEnableBtn = findViewById(R.id.disableEnableButton);
        Button deleteBtn = findViewById(R.id.deleteGuestButton);

        adapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_single_choice, guestRows);
        listView.setChoiceMode(ListView.CHOICE_MODE_SINGLE);
        listView.setAdapter(adapter);

        createBtn.setOnClickListener(v -> createGuest(guestName.getText().toString(), status));
        refreshBtn.setOnClickListener(v -> loadGuests(status));
        disableEnableBtn.setOnClickListener(v -> toggleGuest(listView.getCheckedItemPosition(), status));
        deleteBtn.setOnClickListener(v -> deleteGuest(listView.getCheckedItemPosition(), status));

        loadGuests(status);
    }

    private void loadGuests(TextView status) {
        new Thread(() -> {
            try {
                String response = ApiClient.get("/guests", sessionManager.getToken());
                SharedPreferences prefs = getSharedPreferences(CACHE_PREFS, MODE_PRIVATE);
                prefs.edit().putString(CACHE_GUESTS, response).apply();
                parseGuestResponse(response);
                runOnUiThread(() -> {
                    adapter.notifyDataSetChanged();
                    status.setText("Guests loaded");
                });
            } catch (Exception e) {
                SharedPreferences prefs = getSharedPreferences(CACHE_PREFS, MODE_PRIVATE);
                String cached = prefs.getString(CACHE_GUESTS, null);
                if (cached != null) {
                    parseGuestResponse(cached);
                    runOnUiThread(() -> {
                        adapter.notifyDataSetChanged();
                        status.setText("Offline mode: cached guests");
                    });
                    return;
                }
                runOnUiThread(() -> status.setText("Failed to load guests"));
            }
        }).start();
    }

    private void parseGuestResponse(String response) {
        JsonObject root = JsonParser.parseString(response).getAsJsonObject();
        JsonArray items = root.getAsJsonArray("items");
        guestRows.clear();
        guestIds.clear();
        for (JsonElement item : items) {
            JsonObject obj = item.getAsJsonObject();
            String id = obj.get("id").getAsString();
            String name = obj.get("full_name").getAsString();
            boolean enabled = obj.get("enabled").getAsBoolean();
            guestIds.add(id);
            guestRows.add(name + (enabled ? " (enabled)" : " (disabled)"));
        }
    }

    private void createGuest(String name, TextView status) {
        if (name.trim().isEmpty()) {
            status.setText("Guest name is required");
            return;
        }
        new Thread(() -> {
            try {
                String body = "{\"full_name\":\"" + name + "\"}";
                ApiClient.postJson("/guests", body, sessionManager.getToken());
                runOnUiThread(() -> {
                    status.setText("Guest created");
                    loadGuests(status);
                });
            } catch (Exception e) {
                runOnUiThread(() -> status.setText("Create failed"));
            }
        }).start();
    }

    private void toggleGuest(int index, TextView status) {
        if (index < 0 || index >= guestIds.size()) {
            status.setText("Select a guest first");
            return;
        }

        String row = guestRows.get(index);
        boolean currentlyEnabled = row.contains("enabled");
        new Thread(() -> {
            try {
                String body = "{\"enabled\":" + (!currentlyEnabled) + "}";
                ApiClient.patchJson("/guests/" + guestIds.get(index), body, sessionManager.getToken());
                runOnUiThread(() -> {
                    status.setText("Guest updated");
                    loadGuests(status);
                });
            } catch (Exception e) {
                runOnUiThread(() -> status.setText("Update failed"));
            }
        }).start();
    }

    private void deleteGuest(int index, TextView status) {
        if (index < 0 || index >= guestIds.size()) {
            status.setText("Select a guest first");
            return;
        }

        new Thread(() -> {
            try {
                ApiClient.delete("/guests/" + guestIds.get(index), sessionManager.getToken());
                runOnUiThread(() -> {
                    status.setText("Guest deleted");
                    loadGuests(status);
                });
            } catch (Exception e) {
                runOnUiThread(() -> status.setText("Delete failed"));
            }
        }).start();
    }
}
