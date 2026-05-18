package com.kann.faceiddoor;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public class InviteLinkActivity extends AppCompatActivity {
    private SessionManager sessionManager;
    private String lastLink;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_invite_link);

        sessionManager = new SessionManager(this);
        EditText guestIdField = findViewById(R.id.inviteGuestIdField);
        TextView output = findViewById(R.id.inviteOutput);
        Button generateBtn = findViewById(R.id.generateLinkButton);
        Button copyBtn = findViewById(R.id.copyLinkButton);
        Button shareBtn = findViewById(R.id.shareLinkButton);

        generateBtn.setOnClickListener(v -> generateLink(guestIdField.getText().toString(), output));
        copyBtn.setOnClickListener(v -> copyLink(output));
        shareBtn.setOnClickListener(v -> shareLink(output));
    }

    private void generateLink(String guestId, TextView output) {
        if (guestId.trim().isEmpty()) {
            output.setText("Guest ID is required");
            return;
        }
        new Thread(() -> {
            try {
                String response = ApiClient.postJson("/registration/generate-link", "{\"guest_id\":\"" + guestId + "\"}", sessionManager.getToken());
                JsonObject obj = JsonParser.parseString(response).getAsJsonObject();
                lastLink = ApiClient.BASE_URL + obj.get("registration_url").getAsString();
                runOnUiThread(() -> output.setText(lastLink));
            } catch (Exception e) {
                runOnUiThread(() -> output.setText("Failed to generate link"));
            }
        }).start();
    }

    private void copyLink(TextView output) {
        if (lastLink == null) {
            output.setText("Generate a link first");
            return;
        }
        ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        clipboard.setPrimaryClip(ClipData.newPlainText("Invite Link", lastLink));
        output.setText("Copied: " + lastLink);
    }

    private void shareLink(TextView output) {
        if (lastLink == null) {
            output.setText("Generate a link first");
            return;
        }
        Intent shareIntent = new Intent(Intent.ACTION_SEND);
        shareIntent.setType("text/plain");
        shareIntent.putExtra(Intent.EXTRA_TEXT, lastLink);
        startActivity(Intent.createChooser(shareIntent, "Share invite link"));
    }
}
